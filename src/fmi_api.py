import datetime
from fmiopendata.wfs import download_stored_query
from concurrent.futures import ThreadPoolExecutor
import asyncio
import itertools
import pandas as pd


def get_temp(id, start_str, end_str):
    print(f'task {id} executing {start_str} - {end_str}')
    stations = ['Helsinki', 'Jämsä', 'Oulu', 'Rovaniemi']

    obs = download_stored_query("fmi::observations::weather::multipointcoverage",
                                args=["starttime=" + start_str,
                                      "endtime=" + end_str,
                                      "parameters=T",
                                      "timestep=60",
                                      "timeseries=True",
                                      "place=Helsinki&place=Oulu&place=Jämsä&place=Rovaniemi",
                                      "maxlocations=1"])
    data = obs.data
    all_data = {}
    i = 0
    for key in data.keys():
        times = data[key]['times']
        values = data[key]['T']['values']

        all_data[stations[i]] = {'times': times, 'values': values}
        i += 1
    return all_data


def temperatures(start_time, end_time):

    curr_time = start_time
    end_time = pd.to_datetime(end_time)
    monday1 = (curr_time - datetime.timedelta(days=curr_time.weekday()))
    monday2 = (end_time - datetime.timedelta(days=end_time.weekday()))

    weeks = (monday2 - monday1).days / 7
    # generate 168 hour periods due to API restrictions
    i = 1
    parameters = []
    while curr_time + datetime.timedelta(hours=168) < end_time:
        new_end_time = curr_time + datetime.timedelta(hours=168)
        start_str = curr_time.isoformat(timespec="seconds") + "Z"
        end_str = new_end_time.isoformat(timespec="seconds") + "Z"
        curr_time = curr_time + datetime.timedelta(hours=169)
        parameters.append(tuple((i, start_str, end_str)))
        i += 1

    start_str = curr_time.isoformat(timespec="seconds") + "Z"
    end_str = end_time.isoformat(timespec="seconds") + "Z"

    parameters.append(tuple((i, start_str, end_str)))

    all_dfs = []
    for week in parameters:
        result = get_temp(*week)
        cols = list(result.keys())
        df = pd.DataFrame(columns=cols)
        for col in cols:
            df['Aikaleima'] = result[col]['times']
            df[col] = result[col]['values']
        all_dfs.append(df)
    full_df = pd.concat(all_dfs)
    full_df.set_index(['Aikaleima'], inplace=True)
    full_df.interpolate(inplace=True, axis=1)
    return full_df

