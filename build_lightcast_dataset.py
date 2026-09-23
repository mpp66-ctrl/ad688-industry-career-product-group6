import os, sys
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, trim

spark = (SparkSession.builder
    .appName('LightcastFilter')
    .master('local[*]')
    .config('spark.driver.memory', '4g')
    .config('spark.driver.host', 'localhost')
    .getOrCreate())

US_STATES = ['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware',
'Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine',
'Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada',
'New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma',
'Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont',
'Virginia','Washington','West Virginia','Wisconsin','Wyoming','District of Columbia']

KEYWORDS = ['data scientist','data engineer','machine learning engineer','ml engineer','data analyst',
'business analyst','bi analyst','business intelligence analyst','analytics engineer','applied scientist',
'data architect','database architect']

df = spark.read.option('header', True).option('multiLine', True).option('escape', '"').csv(
    'data/raw_lightcast/lightcast_job_postings.csv')

print('Raw row count:', df.count())

df_naics = df.filter(col('NAICS_2022_3') == '518')
print('After NAICS 518 filter:', df_naics.count())

df_us = df_naics.filter(trim(col('STATE_NAME')).isin(US_STATES))
print('After US-only filter:', df_us.count())

title_lower = lower(col('TITLE_CLEAN'))
keyword_cond = title_lower.contains(KEYWORDS[0])
for k in KEYWORDS[1:]:
    keyword_cond = keyword_cond | title_lower.contains(k)
df_role = df_us.filter(keyword_cond)
print('After role-keyword filter:', df_role.count())

df_dedup = df_role.dropDuplicates(['ID'])
print('After dedup:', df_dedup.count())

result = df_dedup.select(
    col('ID').alias('job_id'),
    col('TITLE_CLEAN').alias('title'),
    col('COMPANY_RAW').alias('company_name_raw'),
    col('COMPANY_NAME').alias('company_name_clean'),
    col('STATE_NAME').alias('state_clean'),
    col('STATE').alias('state_abbr'),
    col('CITY_NAME').alias('city_raw'),
    col('REMOTE_TYPE_NAME').alias('remote_status'),
    col('EMPLOYMENT_TYPE_NAME').alias('employment_type'),
    col('SALARY_FROM').cast('double').alias('salary_min_annual'),
    col('SALARY_TO').cast('double').alias('salary_max_annual'),
    col('MIN_YEARS_EXPERIENCE').alias('experience_min_years'),
    col('EDUCATION_LEVELS_NAME').alias('education_level'),
    col('SOC_5').alias('soc_code'),
    col('SOC_5_NAME').alias('soc_name'),
    col('ONET').alias('onet_code'),
    col('ONET_NAME').alias('onet_name'),
    col('NAICS_2022_6').alias('naics_code'),
    col('NAICS_2022_6_NAME').alias('naics_name'),
    col('SKILLS_NAME').alias('skills'),
    col('POSTED').alias('posted_at'),
    col('URL').alias('apply_url'),
)

result.toPandas().to_csv('data/processed/lightcast_market_panel.csv', index=False)
print('Saved data/processed/lightcast_market_panel.csv')
