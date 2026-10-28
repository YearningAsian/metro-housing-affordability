-- One row per study ZIP (with residential addresses) and month, with its metro: the same columns as
-- mart_metro_month, where county data reaches ZIPs as res_ratio-weighted averages of county rates.
{{ place_month('zip', 'zip') }}
