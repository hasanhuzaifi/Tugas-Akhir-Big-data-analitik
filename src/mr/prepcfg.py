"""Konfigurasi preprocessing MapReduce: kolom mentah (tanpa location), kolom turunan, tipe Parquet.
Dipakai prep_mapper.py (dikirim lewat -files) dan src/load_parquet.py."""
START = "2023-10-25"
CRIME = "id case_number date block iucr primary_type description location_description arrest domestic beat district ward community_area fbi_code x_coordinate y_coordinate year updated_on latitude longitude".split()
CRASHES = ("crash_record_id crash_date_est_i crash_date posted_speed_limit traffic_control_device device_condition weather_condition lighting_condition "
           "first_crash_type trafficway_type lane_cnt alignment roadway_surface_cond road_defect report_type crash_type intersection_related_i "
           "private_property_i hit_and_run_i damage date_police_notified prim_contributory_cause sec_contributory_cause street_no street_direction "
           "street_name beat_of_occurrence photos_taken_i statements_taken_i dooring_i work_zone_i work_zone_type workers_present_i num_units crash_month "
           "most_severe_injury injuries_total injuries_fatal injuries_incapacitating injuries_non_incapacitating injuries_reported_not_evident "
           "injuries_no_indication injuries_unknown crash_hour crash_day_of_week idot_control_no latitude longitude").split()
SR311 = ("sr_number sr_type sr_short_code created_department owner_department status origin created_date last_modified_date closed_date street_address "
         "city state zip_code street_number street_direction street_name street_type duplicate legacy_record legacy_sr_number parent_sr_number "
         "community_area ward electrical_district electricity_grid police_sector police_district police_beat precinct sanitation_division_days "
         "created_hour created_day_of_week created_month x_coordinate y_coordinate latitude longitude").split()
TURUNAN = ["hour", "day_of_week", "month", "is_weekend"]
# nama: (kolom mentah, kolom versi untuk dedup, kolom tanggal, kolom turunan khusus dataset)
DS = {"crime": (CRIME, "updated_on", "date", ["time_missing"]),
      "crashes": (CRASHES, "date_police_notified", "crash_date", ["district"]),
      "311": (SR311, "last_modified_date", "created_date", ["district"])}
# tipe selain string
TIPE = {"date": "timestamp", "crash_date": "timestamp", "created_date": "timestamp", "arrest": "boolean", "domestic": "boolean",
        "district": "int", "latitude": "double", "longitude": "double", "injuries_total": "int", "community_area": "int",
        "hour": "int", "day_of_week": "int", "month": "int", "is_weekend": "boolean", "time_missing": "boolean"}

def kolom(ds):
    """Urutan kolom keluaran: kolom mentah, turunan khusus dataset, fitur waktu."""
    raw, _, _, extra = DS[ds]
    return list(raw) + [c for c in extra if c not in raw] + TURUNAN
