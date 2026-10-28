Column descriptions shared by the int_ models and the marts, referenced from the schema YAML with doc().

{% docs geo_level %}Place type: metro or zip (county in some facts).{% enddocs %}
{% docs geo_code %}Place key: CBSA code for metros, ZIP for ZIPs, county FIPS for counties.{% enddocs %}
{% docs cbsa_code %}5-digit CBSA code of the study metro (July 2023 delineation).{% enddocs %}
{% docs month %}First day of the month.{% enddocs %}

{% docs zhvi_usd %}Zillow Home Value Index: typical value of homes in the 35th-65th percentile, smoothed and seasonally adjusted, in dollars.{% enddocs %}
{% docs median_sale_price_usd %}Redfin median sale price, not seasonally adjusted. ZIPs: rolling three months ending this month.{% enddocs %}
{% docs median_sale_ppsf_usd %}Redfin median sale price per square foot.{% enddocs %}
{% docs median_list_price_usd %}Redfin median list price of new listings.{% enddocs %}
{% docs median_list_ppsf_usd %}Redfin median list price per square foot of new listings.{% enddocs %}
{% docs is_division_blend %}True when Redfin reports the metro as two metro divisions (Dallas-Fort Worth, Seattle) and the values are their sums or homes-sold-weighted averages.{% enddocs %}

{% docs zori_usd %}Zillow Observed Rent Index: typical asking rent, smoothed and seasonally adjusted, in dollars per month.{% enddocs %}
{% docs fmr_2br_usd %}HUD two-bedroom Fair Market Rent in dollars per month: the ZIP's Small Area FMR when HUD publishes one for that fiscal year, else the metro's core FMR area.{% enddocs %}
{% docs fmr_fiscal_year %}HUD fiscal year of fmr_2br_usd; fiscal year N runs from October N-1 to September N.{% enddocs %}
{% docs fmr_is_carried_forward %}True when the month is past the end of fmr_fiscal_year.{% enddocs %}

{% docs homes_sold %}Redfin homes sold. ZIPs: rolling three-month total.{% enddocs %}
{% docs pending_sales %}Redfin pending sales.{% enddocs %}
{% docs new_listings %}Redfin new listings.{% enddocs %}
{% docs active_listings %}Redfin listings active at any point in the period.{% enddocs %}
{% docs inventory %}Redfin listings active at the end of the period.{% enddocs %}
{% docs months_of_supply %}Inventory divided by homes sold per month.{% enddocs %}
{% docs median_days_on_market %}Redfin median days from listing to pending.{% enddocs %}
{% docs sale_to_list_pct %}Redfin average ratio of sale price to final list price, in percent (100 = at list).{% enddocs %}
{% docs sold_above_list_pct %}Redfin share of homes sold above their original list price, in percent.{% enddocs %}
{% docs off_market_in_two_weeks_pct %}Redfin share of listings that went pending within two weeks, in percent.{% enddocs %}

{% docs permit_units %}Housing units authorized by building permits this month, summed over the metro's counties. Null for ZIPs: counts are not split across ZIPs.{% enddocs %}
{% docs permits_per_1000 %}Units permitted over the trailing 12 months per 1,000 residents (ACS population). Null for 2015 before 12 months exist. ZIPs: res_ratio-weighted average of their counties' rates.{% enddocs %}

{% docs employment %}QCEW all-industry employment in the month. Null for ZIPs.{% enddocs %}
{% docs avg_weekly_wage_usd %}QCEW average weekly wage for the quarter, in dollars. ZIPs: res_ratio-weighted average of their counties' wages.{% enddocs %}
{% docs wages_quarter %}QCEW quarter the wage values come from, e.g. 2026Q1.{% enddocs %}
{% docs wages_is_carried_forward %}True when the month is after the latest QCEW month (QCEW lags about six months).{% enddocs %}
{% docs unemployment_rate_pct %}BLS LAUS metro unemployment rate, not seasonally adjusted, in percent. ZIPs get their metro's rate.{% enddocs %}

{% docs net_migration_people %}IRS net migration: people moving in minus people moving out over the tax year, summed over the metro's counties. Null for ZIPs.{% enddocs %}
{% docs net_migration_rate %}Net migration per 1,000 residents (ACS population). ZIPs: res_ratio-weighted average of their counties' rates.{% enddocs %}
{% docs migration_tax_year %}IRS tax year of the migration values; it applies from January of that year.{% enddocs %}
{% docs migration_is_carried_forward %}True when the month's year is after migration_tax_year.{% enddocs %}

{% docs median_household_income_usd %}ACS 5-year median household income, in dollars. ZIPs: the ZCTA with the same code.{% enddocs %}
{% docs population %}ACS 5-year total population.{% enddocs %}
{% docs median_gross_rent_usd %}ACS 5-year median gross rent (rent plus utilities), in dollars per month.{% enddocs %}
{% docs rent_pct_income %}ACS 5-year median gross rent as a percentage of household income.{% enddocs %}
{% docs income_acs_vintage %}ACS 5-year vintage (its last year) of the income values; it applies from January of that year.{% enddocs %}
{% docs income_is_carried_forward %}True when the month's year is after income_acs_vintage.{% enddocs %}

{% docs mortgage_rate_pct %}Freddie Mac 30-year fixed mortgage rate (FRED MORTGAGE30US), monthly average of the weekly rates, in percent.{% enddocs %}
{% docs cpi %}US CPI for all urban consumers (FRED CPIAUCSL), seasonally adjusted, 1982-84 = 100.{% enddocs %}
{% docs price_to_income %}zhvi_usd divided by median_household_income_usd.{% enddocs %}
{% docs rent_to_wage %}zori_usd divided by a month of the average weekly wage (avg_weekly_wage_usd * 52 / 12).{% enddocs %}
{% docs zhvi_yoy_growth %}Change in zhvi_usd from the same month a year earlier, as a fraction (0.05 = 5%).{% enddocs %}
{% docs zori_yoy_growth %}Change in zori_usd from the same month a year earlier, as a fraction.{% enddocs %}
{% docs avg_weekly_wage_yoy_growth %}Change in avg_weekly_wage_usd from the same month a year earlier, as a fraction.{% enddocs %}
{% docs employment_yoy_growth %}Change in employment from the same month a year earlier, as a fraction.{% enddocs %}
