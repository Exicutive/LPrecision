"""Services for estate master layouts.

The service deliberately keeps storage, validation, versioning and review
separate from HTTP views.  It has a conservative built-in reader for standard
ASCII DXF LWPOLYLINE boundaries and GeoJSON polygons.  More specialised DXF
objects and Shapefile packages still require a GIS worker; they are never
silently interpreted as parcel boundaries.
"""

import hashlib
import json
import os
import zipfile
from collections import Counter
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.master_layouts.models import (
    EstateMasterPlan,
    ExtractedParcelCandidate,
    MasterLayoutProcessingJob,
)
from apps.parcels.models import Parcel


MAX_LAYOUT_BYTES = 50 * 1024 * 1024
FORMAT_BY_EXTENSION = {
    ".geojson": EstateMasterPlan.Format.GEOJSON,
    ".json": EstateMasterPlan.Format.GEOJSON,
    ".dxf": EstateMasterPlan.Format.DXF,
    ".zip": EstateMasterPlan.Format.SHAPEFILE_ZIP,
}


class LayoutUploadError(ValueError):
    pass


class MasterLayoutUploadService:
    @staticmethod
    def _read(uploaded_file):
        uploaded_file.seek(0)
        content = uploaded_file.read()
        uploaded_file.seek(0)
        return content

    @classmethod
    def validate(cls, uploaded_file):
        if not uploaded_file or not uploaded_file.name:
            raise LayoutUploadError("Choose an estate master layout file.")
        filename = os.path.basename(uploaded_file.name)
        extension = os.path.splitext(filename)[1].lower()
        file_format = FORMAT_BY_EXTENSION.get(extension)
        if not file_format:
            raise LayoutUploadError("Supported master-layout formats are GeoJSON, DXF, and a Shapefile ZIP.")
        if uploaded_file.size <= 0:
            raise LayoutUploadError("The uploaded layout file is empty.")
        if uploaded_file.size > MAX_LAYOUT_BYTES:
            raise LayoutUploadError("Master layout files must be 50 MB or smaller.")

        content = cls._read(uploaded_file)
        if file_format == EstateMasterPlan.Format.GEOJSON:
            try:
                document = json.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise LayoutUploadError("The GeoJSON file is not valid UTF-8 JSON.") from error
            if not isinstance(document, dict) or document.get("type") not in {"FeatureCollection", "Feature"}:
                raise LayoutUploadError("The GeoJSON must contain a FeatureCollection or Feature.")
        elif file_format == EstateMasterPlan.Format.DXF:
            sample = content[:4096].decode("latin-1", errors="ignore").upper()
            if "SECTION" not in sample or "EOF" not in content[-4096:].decode("latin-1", errors="ignore").upper():
                raise LayoutUploadError("The DXF file does not have a recognizable DXF structure.")
        else:
            try:
                with zipfile.ZipFile(uploaded_file) as archive:
                    names = archive.namelist()
                    if any(name.startswith(("/", "\\")) or ".." in name.replace("\\", "/").split("/") for name in names):
                        raise LayoutUploadError("The Shapefile ZIP contains an unsafe file path.")
                    suffixes = {os.path.splitext(name)[1].lower() for name in names}
                    if not {".shp", ".shx", ".dbf"}.issubset(suffixes):
                        raise LayoutUploadError("The ZIP must contain .shp, .shx, and .dbf files.")
            except zipfile.BadZipFile as error:
                raise LayoutUploadError("The uploaded Shapefile package is not a valid ZIP archive.") from error
            finally:
                uploaded_file.seek(0)

        return filename, file_format, hashlib.sha256(content).hexdigest()

    @classmethod
    def create(cls, *, estate, user, uploaded_file):
        filename, file_format, checksum = cls.validate(uploaded_file)
        with transaction.atomic():
            # Serialise version allocation for one estate.
            estate = type(estate).objects.select_for_update().get(pk=estate.pk)
            existing = estate.master_plans.filter(checksum=checksum).exclude(
                processing_status=EstateMasterPlan.Status.SUPERSEDED
            ).first()
            if existing:
                job, _ = MasterLayoutProcessingJob.objects.get_or_create(
                    master_plan=existing,
                    attempt=1,
                    defaults={"company": estate.company, "estate": estate, "stage": "Waiting for processing"},
                )
                return existing, job, False
            version = (estate.master_plans.aggregate(max_version=Max("version"))["max_version"] or 0) + 1
            plan = EstateMasterPlan.objects.create(
                company=estate.company,
                estate=estate,
                original_filename=filename,
                document=uploaded_file,
                file_format=file_format,
                file_size=uploaded_file.size,
                checksum=checksum,
                uploaded_by=user,
                version=version,
                processing_status=EstateMasterPlan.Status.QUEUED,
            )
            job = MasterLayoutProcessingJob.objects.create(
                company=estate.company,
                estate=estate,
                master_plan=plan,
                stage="Waiting for processing",
            )
        return plan, job, True


class GeometryValidationService:
    @staticmethod
    def polygon_ring(value):
        warnings = []
        if not isinstance(value, list) or len(value) < 4:
            return [], ["Polygon boundary requires at least four coordinate points."]
        points = []
        for point in value:
            if not isinstance(point, list) or len(point) < 2 or not all(isinstance(axis, (int, float)) for axis in point[:2]):
                return [], ["Polygon coordinates must contain numeric X and Y values."]
            points.append(point)
        if points[0][:2] != points[-1][:2]:
            warnings.append("Polygon boundary is not closed.")
        return points, warnings


class LayoutExtractionService:
    PLOT_KEYS = ("plot_number", "plot_no", "plot", "parcel_id", "id")
    BLOCK_KEYS = ("block", "block_id", "block_number")

    @staticmethod
    def crs(document):
        crs = document.get("crs") if isinstance(document, dict) else None
        if isinstance(crs, str):
            return crs.strip()
        if isinstance(crs, dict):
            properties = crs.get("properties")
            if isinstance(properties, dict) and isinstance(properties.get("name"), str):
                return properties["name"].strip()
        metadata = document.get("metadata", {}) if isinstance(document, dict) else {}
        return str(metadata.get("crs", "")).strip() if isinstance(metadata, dict) else ""

    @classmethod
    def features(cls, document):
        if document.get("type") == "FeatureCollection":
            return document.get("features") if isinstance(document.get("features"), list) else []
        return [document] if document.get("type") == "Feature" else []

    @staticmethod
    def first_property(properties, keys):
        for key in keys:
            value = properties.get(key)
            if value not in (None, ""):
                return str(value).strip()
        return ""

    @classmethod
    def extract(cls, plan):
        with plan.document.open("rb") as layout_file:
            document = json.loads(layout_file.read().decode("utf-8"))
        features = cls.features(document)
        known_crs = cls.crs(document)
        records = []
        plot_numbers = []
        for index, feature in enumerate(features):
            properties = feature.get("properties") if isinstance(feature, dict) and isinstance(feature.get("properties"), dict) else {}
            geometry = feature.get("geometry") if isinstance(feature, dict) and isinstance(feature.get("geometry"), dict) else {}
            warnings = []
            coordinates = []
            if geometry.get("type") != "Polygon":
                warnings.append("Only single Polygon features can be automatically reviewed.")
            else:
                rings = geometry.get("coordinates")
                coordinates, geometry_warnings = GeometryValidationService.polygon_ring(rings[0] if isinstance(rings, list) and rings else [])
                warnings.extend(geometry_warnings)
            if not known_crs:
                warnings.append("Coordinate reference system (CRS) is missing or ambiguous; it was not assumed.")
            plot_number = cls.first_property(properties, cls.PLOT_KEYS)
            block = cls.first_property(properties, cls.BLOCK_KEYS)
            if not plot_number:
                warnings.append("Plot identifier is missing.")
            plot_numbers.append(plot_number)
            records.append({
                "source_feature_index": index,
                "plot_number": plot_number,
                "block": block,
                "boundary_coordinates": coordinates,
                "original_boundary_coordinates": geometry.get("coordinates", []) if isinstance(geometry, dict) else [],
                "warnings": warnings,
                "metadata": {"properties": properties, "geometry_type": geometry.get("type", "")},
            })
        duplicates = {value for value, count in Counter(number for number in plot_numbers if number).items() if count > 1}
        for record in records:
            if record["plot_number"] in duplicates:
                record["warnings"].append("Duplicate plot identifier in this master layout.")
        return records, known_crs


class DxfLayoutExtractionService:
    """Extract only explicit, closed, standard LWPOLYLINE boundaries from DXF.

    Civil 3D proxy objects, arcs, hatches and unclosed linework are intentionally
    ignored.  A DXF does not reliably embed its CRS or plot identifiers, so the
    result always remains in the administrator's review queue.
    """

    @staticmethod
    def _pairs(raw):
        lines = raw.decode("latin-1", errors="replace").replace("\ufeff", "").splitlines()
        return [(lines[index].strip(), lines[index + 1].strip()) for index in range(0, len(lines) - 1, 2)]

    @classmethod
    def _entities(cls, pairs):
        inside_entities = False
        entity = None
        for code, value in pairs:
            if code == "0" and value == "SECTION":
                entity = None
                continue
            if code == "2" and value == "ENTITIES" and not inside_entities:
                inside_entities = True
                continue
            if not inside_entities:
                continue
            if code == "0" and value == "ENDSEC":
                if entity:
                    yield entity
                return
            if code == "0":
                if entity:
                    yield entity
                entity = {"type": value, "groups": []}
            elif entity:
                entity["groups"].append((code, value))
        if entity:
            yield entity

    @staticmethod
    def _float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _polyline(cls, entity):
        if entity["type"] != "LWPOLYLINE":
            return None
        groups = entity["groups"]
        layer = next((value for code, value in groups if code == "8"), "")
        flags = next((value for code, value in groups if code == "70"), "0")
        try:
            is_closed = bool(int(flags) & 1)
        except ValueError:
            is_closed = False
        points = []
        current_x = None
        for code, value in groups:
            if code == "10":
                current_x = cls._float(value)
            elif code == "20" and current_x is not None:
                current_y = cls._float(value)
                if current_y is not None:
                    points.append([current_x, current_y])
                current_x = None
        if not is_closed or len(points) < 3:
            return None
        if points[0] != points[-1]:
            points.append(points[0])
        return layer, points

    @classmethod
    def extract(cls, plan):
        with plan.document.open("rb") as layout_file:
            entities = cls._entities(cls._pairs(layout_file.read()))
            polylines = [polyline for entity in entities if (polyline := cls._polyline(entity))]
        records = []
        for source_index, (layer, points) in enumerate(polylines):
            records.append({
                "source_feature_index": source_index,
                "plot_number": "",
                "block": layer,
                "boundary_coordinates": points,
                "original_boundary_coordinates": points,
                "warnings": [
                    "DXF coordinate reference system (CRS) is not embedded; it was not assumed.",
                    "DXF boundary has no reliable plot identifier. Review and identify it before publication.",
                ],
                "metadata": {"source_type": "LWPOLYLINE", "source_layer": layer},
            })
        return records, ""


class MasterLayoutProcessingService:
    @classmethod
    def process(cls, *, plan, job):
        if plan.file_format == EstateMasterPlan.Format.SHAPEFILE_ZIP:
            message = "Shapefile processing requires the GIS worker, which is not configured in this installation. The original package remains stored safely."
            now = timezone.now()
            plan.processing_status = EstateMasterPlan.Status.FAILED
            plan.processing_error = message
            plan.processing_completed_at = now
            plan.save(update_fields=("processing_status", "processing_error", "processing_completed_at"))
            job.status = MasterLayoutProcessingJob.Status.FAILED
            job.error = message
            job.completed_at = now
            job.stage = "Processing engine not configured"
            job.save(update_fields=("status", "error", "completed_at", "stage", "updated_at"))
            return plan, job

        now = timezone.now()
        plan.processing_status = EstateMasterPlan.Status.PROCESSING
        plan.processing_started_at = now
        plan.processing_error = ""
        plan.save(update_fields=("processing_status", "processing_started_at", "processing_error"))
        job.status = MasterLayoutProcessingJob.Status.PROCESSING
        job.started_at = now
        job.stage = "Extracting polygon boundaries"
        job.error = ""
        job.save(update_fields=("status", "started_at", "stage", "error", "updated_at"))
        try:
            if plan.file_format == EstateMasterPlan.Format.GEOJSON:
                records, crs = LayoutExtractionService.extract(plan)
            else:
                records, crs = DxfLayoutExtractionService.extract(plan)
            if not records:
                raise ValueError("No supported closed polygon boundaries were found.")
            with transaction.atomic():
                for record in records:
                    warnings = record.pop("warnings")
                    status = ExtractedParcelCandidate.Status.VALIDATED if not warnings else ExtractedParcelCandidate.Status.NEEDS_REVIEW
                    ExtractedParcelCandidate.objects.update_or_create(
                        master_plan=plan,
                        source_feature_index=record["source_feature_index"],
                        defaults={
                            "company": plan.company,
                            "estate": plan.estate,
                            "plot_number": record["plot_number"],
                            "block": record["block"],
                            "boundary_coordinates": record["boundary_coordinates"],
                            "original_boundary_coordinates": record["original_boundary_coordinates"],
                            "status": status,
                            "validation_warnings": warnings,
                            "metadata": record["metadata"],
                        },
                    )
                needs_review = ExtractedParcelCandidate.objects.filter(master_plan=plan, status=ExtractedParcelCandidate.Status.NEEDS_REVIEW).count()
                summary = {
                    "total_features": len(records),
                    "validated": len(records) - needs_review,
                    "needs_review": needs_review,
                    "coordinate_reference_system": crs or None,
                    "warnings": ["Area, perimeter, topology, and overlap analysis require a configured GIS processing engine."],
                }
                now = timezone.now()
                plan.coordinate_reference_system = crs
                plan.processing_metadata = summary
                plan.processing_completed_at = now
                plan.processing_status = EstateMasterPlan.Status.REVIEW_REQUIRED if needs_review else EstateMasterPlan.Status.READY_FOR_APPROVAL
                plan.save(update_fields=("coordinate_reference_system", "processing_metadata", "processing_completed_at", "processing_status"))
                job.metadata = summary
                job.completed_at = now
                job.stage = "Review extracted parcel candidates"
                job.status = MasterLayoutProcessingJob.Status.REVIEW_REQUIRED if needs_review else MasterLayoutProcessingJob.Status.COMPLETED
                job.save(update_fields=("metadata", "completed_at", "stage", "status", "updated_at"))
        except (UnicodeDecodeError, json.JSONDecodeError, OSError, ValueError) as error:
            now = timezone.now()
            plan.processing_status = EstateMasterPlan.Status.FAILED
            plan.processing_error = "The master layout could not be processed safely."
            plan.processing_completed_at = now
            plan.save(update_fields=("processing_status", "processing_error", "processing_completed_at"))
            job.status = MasterLayoutProcessingJob.Status.FAILED
            job.error = "The master layout could not be processed safely."
            job.completed_at = now
            job.stage = "Processing failed"
            job.save(update_fields=("status", "error", "completed_at", "stage", "updated_at"))
        return plan, job


class ParcelGenerationService:
    @staticmethod
    def _mark_current_if_resolved(plan):
        """A replacement becomes current only after a review leaves no open candidates."""
        plan = EstateMasterPlan.objects.select_for_update().get(pk=plan.pk)
        candidates = plan.parcel_candidates
        if (
            candidates.filter(status=ExtractedParcelCandidate.Status.APPROVED).exists()
            and not candidates.exclude(
                status__in=[ExtractedParcelCandidate.Status.APPROVED, ExtractedParcelCandidate.Status.REJECTED]
            ).exists()
        ):
            plan.estate.master_plans.filter(is_current=True).exclude(pk=plan.pk).update(
                is_current=False, processing_status=EstateMasterPlan.Status.SUPERSEDED
            )
            plan.is_current = True
            plan.processing_status = EstateMasterPlan.Status.APPROVED
            plan.save(update_fields=("is_current", "processing_status"))

    @classmethod
    def approve(cls, *, plan, candidates, user):
        """Publish validated candidates atomically; no allocation or title is created."""
        approved = []
        with transaction.atomic():
            candidates = candidates.select_for_update()
            for candidate in candidates:
                if candidate.status not in {ExtractedParcelCandidate.Status.VALIDATED, ExtractedParcelCandidate.Status.APPROVED}:
                    continue
                if candidate.published_parcel_id:
                    approved.append(candidate.published_parcel)
                    continue
                if not candidate.plot_number:
                    continue
                if Parcel.objects.select_for_update().filter(estate=plan.estate, plot_number=candidate.plot_number).exists():
                    candidate.status = ExtractedParcelCandidate.Status.NEEDS_REVIEW
                    candidate.validation_warnings = [*candidate.validation_warnings, "A parcel with this plot identifier already exists in the estate."]
                    candidate.save(update_fields=("status", "validation_warnings", "updated_at"))
                    continue
                parcel = Parcel.objects.create(
                    estate=plan.estate,
                    plot_number=candidate.plot_number,
                    block=candidate.block,
                    area_sqm=candidate.area_sqm,
                    perimeter_m=candidate.perimeter_m,
                    boundary_coordinates=candidate.boundary_coordinates,
                    original_boundary_coordinates=candidate.original_boundary_coordinates,
                    source_master_plan=plan,
                    extraction_status="approved",
                )
                candidate.status = ExtractedParcelCandidate.Status.APPROVED
                candidate.reviewed_by = user
                candidate.reviewed_at = timezone.now()
                candidate.published_parcel = parcel
                candidate.save(update_fields=("status", "reviewed_by", "reviewed_at", "published_parcel", "updated_at"))
                approved.append(parcel)
            cls._mark_current_if_resolved(plan)
        return approved

    @classmethod
    def reject(cls, *, candidates, user):
        with transaction.atomic():
            plan = candidates.select_related("master_plan").first().master_plan if candidates.exists() else None
            rejected = candidates.exclude(status=ExtractedParcelCandidate.Status.APPROVED).update(
                status=ExtractedParcelCandidate.Status.REJECTED,
                reviewed_by=user,
                reviewed_at=timezone.now(),
            )
            if plan:
                cls._mark_current_if_resolved(plan)
        return rejected
