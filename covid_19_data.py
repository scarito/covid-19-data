import datetime
import os

import numpy as np
import pandas as pd
import us_state_abbrev

def LoadAllJhuData(path=None):
  if not path:
    path = os.path.join(os.path.dirname(__file__),
                        'COVID-19/csse_covid_19_data/csse_covid_19_daily_reports')
  all_dfs = {}

  for f in sorted(os.listdir(path)):
    full_path = os.path.join(path, f)
    if not os.path.isfile(full_path):
      continue
    if not f.endswith('.csv'):
      continue
    df = pd.read_csv(full_path)
    report_date = np.datetime64(datetime.datetime.strptime(
      f.split('.')[0], '%m-%d-%Y'))
    df['Report_Date'] = pd.Series([np.datetime64(report_date)
                                   for _ in range(df.shape[0])])
    if report_date < np.datetime64('2020-03-22'):
      # Renormalize data.
      df.rename(columns={
        'Province/State': 'Province_State',
        'Country/Region': 'Country_Region',
        'Last Update': 'Last_Update',
      }, inplace=True)
      if report_date >= np.datetime64('2020-03-01'):
        df.rename(columns={
          'Latitude': 'Lat',
          'Longitude': 'Long_',
        }, inplace=True)
      df['Admin2'] = pd.Series(dtype='str')
      df['Combined_Key'] = pd.Series(dtype='str')
      df['Active'] = df['Confirmed'] - df['Deaths'] - df['Recovered']
      for index in range(df.shape[0]):
        if df['Country_Region'][index] == 'US':
          loc = df['Province_State'][index]
          # Get rid of quotes, extra spaces, etc
          loc = loc.replace('"','').replace('\'','').strip()
          # Get rid of "From diamond princess..."
          loc = df['Province_State'][index].split(' (')[0]
          state_tok = loc.split(',')
          state_tok = [s.strip() for s in state_tok]
          if len(state_tok) < 2:
            state_abbrev = state_tok[0]
            region = 'Unassigned'
          else:
            region, state_abbrev = state_tok

          region = region.split(' County')[0]
          if len(state_abbrev) == 2 and state_abbrev != 'US':  # wtf...
            state = us_state_abbrev.abbrev_us_state[state_abbrev]
          else:
            state = state_abbrev
          df.at[index, 'Province_State'] = state
          df.at[index, 'Admin2'] = region
          df.at[index, 'Combined_Key'] = '%s, %s, US' % (region, state)
        else:
          country = df['Country_Region'][index]
          state = str(df['Province_State'][index])
          # Map country/region names back to how they are currently reporting.
          if 'Hong Kong' in country or 'Hong Kong' in state:
            country = 'China'
            state = 'Hong Kong'
          elif 'Macau' in country or 'Macao' in country or 'Macau' in state or 'Macao' in state:
            country = 'China'
            state = 'Macau'
          elif 'Taiwan' in country or 'Taipei' in country or 'Taiwan' in state or 'Taipei' in state:
            country = 'Taiwan*'
            state = None
          elif 'China' in country:
            country = 'China'
          elif 'UK' in country:
            country = 'United Kingdom'
          elif 'Vatican' in country:
            country = 'Holy See'
          # There is a North Ireland on 2-28 but data is consistent with Rep of Ireland timeseries.
          elif 'Ireland' in country:
            country = 'Ireland'
          elif 'South Korea' in country or 'Republic of Korea' in country:
            country = 'Korea, South'
          if state and state != 'nan':
            df.at[index, 'Combined_Key'] = '%s, %s' % (state, country)
            df.at[index, 'Country_Region'] = country
            df.at[index, 'Province_State'] = state
          else:
            df.at[index, 'Combined_Key'] = country
            df.at[index, 'Country_Region'] = country

    # Fix common formatting issues.
    df['Combined_Key'] = df['Combined_Key'].str.replace(', ', ',').str.replace(',', ', ').str.strip()
    df['Country_Region'] = df['Country_Region'].str.strip()
    df['Province_State'] = df['Province_State'].str.strip()
    df['Admin2'] = df['Admin2'].str.strip()

    # Strip off the date in ISO format and use as key.
    all_dfs[str(report_date)[:10]] = df

  return all_dfs

def CreateCombinedDataframe(all_dfs):
  return pd.concat([df for _, df in sorted(all_dfs.items())])

def CreateTimeseries(all_dfs, generate_local=True, generate_province=True, generate_country=True,
                     generate_total=True):
  def collect_rows(all_dfs, key, filt):
    rows = []
    for date in sorted(all_dfs.keys()):
      df = all_dfs[date]
      result = df[filt(df)]
      rows.append({
        'Location': key,
        'Date': np.datetime64(date),
        'Confirmed': result['Confirmed'].sum(min_count=1),
        'Deaths': result['Deaths'].sum(min_count=1),
        'Recovered': result['Recovered'].sum(min_count=1),
        'Active': result['Active'].sum(min_count=1),
      })
    return rows

  combined_df = CreateCombinedDataframe(all_dfs)

  # Generate timeseries rollups
  timeseries_rows = []
  keys_used = set()

  if generate_total:
    # Total
    timeseries_rows += collect_rows(all_dfs, 'Global', lambda x : x.Country_Region == x.Country_Region)

  if generate_country:
    # Rollup by country
    keys = sorted(set(combined_df['Country_Region']))
    for key in keys:
      print(key)
      if key in keys_used:
        print('Duplicate, skipping...')
        continue
      keys_used.add(key)
      timeseries_rows += collect_rows(all_dfs, key, lambda x : x.Country_Region == key)

  if generate_province:
    # Rollup by state/prov
    state_countries = sorted(set([(r.Province_State, r.Country_Region)
                                  for _, r in combined_df[pd.notna(combined_df.Province_State)].iterrows()]))
    for state, country in state_countries:
      key = "%s, %s" % (state, country)
      print(key)
      if key in keys_used:
        print('Duplicate, skipping...')
        continue
      keys_used.add(key)
      timeseries_rows += collect_rows(all_dfs, key,
                                      lambda x : (x.Country_Region == country) & (x.Province_State == state))

  if generate_local:
    # Per key location data
    keys = sorted(set(combined_df['Combined_Key']))
    print(len(keys))
    for key in keys:
      print(key)
      if key in keys_used:
        print('Duplicate, skipping...')
        continue
      keys_used.add(key)
      timeseries_rows += collect_rows(all_dfs, key, lambda x : x.Combined_Key == key)
    
  timeseries = pd.DataFrame(timeseries_rows)
  return timeseries

