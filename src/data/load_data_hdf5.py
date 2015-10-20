# Author: Michal Lukac, cospelthetraceur@gmail.com
# script for geting hdf5 dataset for rossmann kaggle competition
# You need to have pandas, numpy

from pandas import HDFStore
import pandas as pd
import numpy as np
from math import ceil
from sklearn import preprocessing

def get_mean(dft, dfs):
    """
    Get features of mean for every store.
    """
    stores = dfs['Store'].unique()
    days = dft['DayOfWeek'].unique()
    months = dft['Month'].unique()

    mean_visits = []
    mean_sales = []
    mean_sales_days = { k: [] for k in days }
    mean_sales_months = { k: [] for k in months }

    # for every store we get mean value of sales(entire, DayOfWeek, Month)
    for store in stores:
        serie = dft[dft['Store'] == store]
        # entire data mean
        mean_sales.append(serie['Sales'].mean())
        mean_visits.append(serie['Customers'].mean())

        # specific mean
        for day in days:
            mean_sales_days[day].append(serie[serie['DayOfWeek'] == day]['Sales'].mean())
        for month in months:
            mean_sales_months[month].append(serie[serie['Month'] == month]['Sales'].mean())

    # create dataframes
    df = pd.DataFrame({'Store': stores,
                       'MeanVisits': mean_visits,
                       'MeanSales': mean_sales})

    mean_sales_days = rename_dictionary(mean_sales_days, 'MeanDayOfWeekSales')
    mean_sales_days['Store'] = stores
    df_days = pd.DataFrame(mean_sales_days)

    mean_sales_months = rename_dictionary(mean_sales_months, 'MeanMonthSales')
    mean_sales_months['Store'] = stores
    df_months = pd.DataFrame(mean_sales_months)

    # and normalize
    min_max_scaler = preprocessing.MinMaxScaler()
    df['MeanSales'] = min_max_scaler.fit_transform(df['MeanSales'])
    df['MeanVisits'] = min_max_scaler.fit_transform(df['MeanVisits'])

    for day in days:
        df_days['MeanDayOfWeekSales'+str(day)] = min_max_scaler.fit_transform(df_days['MeanDayOfWeekSales'+str(day)])

    for month in months:
        df_months['MeanMonthSales'+str(month)] = min_max_scaler.fit_transform(df_months['MeanMonthSales'+str(month)])

    # merge everything
    return pd.merge(df, pd.merge(df_days, df_months, on='Store'), on='Store')

def rename_dictionary(dictionary, name):
    keys = dictionary.keys()
    for key in keys:
        dictionary[name+str(key)] = dictionary.pop(key)
    return dictionary

def load_data_file(filename,dtypes,parsedate = True):
    """
    Load file to dataframe.
    """
    date_parse = lambda x: pd.datetime.strptime(x, '%Y-%m-%d')
    if parsedate:
        return pd.read_csv(filename, sep=',', parse_dates=['Date'], date_parser= date_parse,dtype=dtypes)
    else:
        return pd.read_csv(filename, sep=',', dtype=dtypes)

def week_of_month(dt):
    """
    Returns the week of the month for the specified date.
    """

    first_day = dt.replace(day=1)

    dom = dt.day
    adjusted_dom = dom + first_day.weekday()

    return int(ceil(adjusted_dom/7.0))

def replace_values(dataframe, column, dictionary):
    """
    Replace values of dataframe column with dictionary values.
    """
    return dataframe[column].apply( lambda x: int(dictionary[x]) )

# some known things about dataset
StateHoliday = {'a': 1, 'b': 2, 'c': 3, '0': 0, 0: 0}
Assortment = {'a': 0, 'b': 1, 'c': 2}
StoreType = {'a': 0,'b': 1,'c': 2, 'd': 3}
Year = { '2013': 1, '2014': 2, '2015': 3 }

# Load data, parse data, clean unwanted columns, replace nan values, create column
print('Loading data ...')
data_dir = '../../data/'
data_train = load_data_file(data_dir + 'train.csv',
                            {'Id':np.int32,
                             'Store':np.int32,
                             'DayOfWeek':np.int8,
                             'Sales':np.int32,
                             'Customers':np.int32,
                             'Open':np.int8,
                             'Promo':np.int8,
                             'StateHoliday':np.object, # categorical
                             'SchoolHoliday':np.int8})

data_test = load_data_file(data_dir + 'test.csv',
                            {'Id':np.int32,
                             'Store':np.int32,
                             'DayOfWeek':np.int8,
                             'Open':np.object,         # there is some nan values
                             'Promo':np.int8,
                             'StateHoliday':np.object, # categorical
                             'SchoolHoliday':np.int8})

data_store = load_data_file(data_dir + 'store.csv',
                            {'Store':np.int32,
                             'StoreType':np.object,
                             'Assortment':np.object,
                             'CompetitionDistance':np.float32,
                             'CompetitionOpenSiceMonth':np.object, # categorical
                             'CompetitionOpenSiceYear':np.object,
                             'Promo2':np.int8,
                             'Promo2SinceWeek':np.object,
                             'Promo2SinceYear':np.object,
                             'PromoInterval':np.object}, False)

print('Add some more features ...')
# we have dayofweek already
data_train['Year'] = data_train['Date'].apply(lambda x: str(x)[:4])
data_train['Year'] = replace_values(data_train, 'Year', Year).astype(np.int8)
data_train['Month'] = data_train['Date'].apply(lambda x: int(str(x)[5:7]))
data_train['WeekOfMonth'] = data_train['Date'].apply(lambda x: int(week_of_month(x)))
data_test['Year'] = data_test['Date'].apply(lambda x: str(x)[:4])
data_test['Month'] = data_test['Date'].apply(lambda x: int(str(x)[5:7]))
data_test['WeekOfMonth'] = data_test['Date'].apply(lambda x: int(week_of_month(x)))
data_test['Year'] = replace_values(data_test, 'Year', Year).astype(np.int8)

print('Replacing values as ...')
# categorical values to binary vectors for neural network
data_train = pd.concat([data_train, pd.core.reshape.get_dummies(data_train['StateHoliday'],dummy_na=True, prefix='StateHoliday')],axis=1)
data_test = pd.concat([data_test, pd.get_dummies(data_test['StateHoliday'],dummy_na=True,prefix='StateHoliday')],axis=1)
data_train = pd.concat([data_train, pd.core.reshape.get_dummies(data_train['WeekOfMonth'],dummy_na=True, prefix='WeekOfMonth')],axis=1)
data_test = pd.concat([data_test, pd.core.reshape.get_dummies(data_test['WeekOfMonth'],dummy_na=True, prefix='WeekOfMonth')],axis=1)
data_train = pd.concat([data_train, pd.core.reshape.get_dummies(data_train['Year'],dummy_na=True, prefix='Year')],axis=1)
data_test = pd.concat([data_test, pd.core.reshape.get_dummies(data_test['Year'],dummy_na=True, prefix='Year')],axis=1)
data_train = pd.concat([data_train, pd.core.reshape.get_dummies(data_train['Month'],dummy_na=True, prefix='Month')],axis=1)
data_test = pd.concat([data_test, pd.core.reshape.get_dummies(data_test['Month'],dummy_na=True, prefix='Month')],axis=1)
data_train = pd.concat([data_train, pd.core.reshape.get_dummies(data_train['DayOfWeek'],dummy_na=True, prefix='DayOfWeek')],axis=1)
data_test = pd.concat([data_test, pd.core.reshape.get_dummies(data_test['DayOfWeek'],dummy_na=True, prefix='DayOfWeek')],axis=1)


# in datatest column some columns is missing so we need to add it with default 0
for column in data_train.columns.values.tolist():
    if column not in data_test.columns.values.tolist():
        data_test[column] = 0

data_store = pd.concat([data_store, pd.core.reshape.get_dummies(data_store['Assortment'],dummy_na=True, prefix='Assortment')],axis=1)
data_store = pd.concat([data_store, pd.core.reshape.get_dummies(data_store['StoreType'],dummy_na=True, prefix='StoreType')],axis=1)

# this is simple converting to integer
data_train['StateHoliday'] = replace_values(data_train,'StateHoliday', StateHoliday).astype(np.int8)
data_test['StateHoliday'] = replace_values(data_test,'StateHoliday', StateHoliday).astype(np.int8)
data_store['Assortment'] = replace_values(data_store,'Assortment', Assortment).astype(np.int8)
data_store['StoreType'] = replace_values(data_store,'StoreType', StoreType).astype(np.int8)

# create mean dataframe
print('Mean data frame values ...')
data_mean =  get_mean(data_train, data_store)

print('Missing values handling ...')
# mean or max missing values
maxCompetitionDistance = max(data_store['CompetitionDistance'].tolist())
meanCompetitionDistance = np.mean(data_store.CompetitionDistance)
data_store['CompetitionDistance'] = data_store['CompetitionDistance'].fillna(meanCompetitionDistance)
data_store['CompetitionDistance'] = data_store['CompetitionDistance'].astype(np.float32)

# binary missing values
# classical replacement will be -1 for negatives, 0 for missing, 1 for positives
# but in open column there is really small amount of missing values
data_test.loc[data_test.Open.isnull(), 'Open'] = 1
data_test['Open'] = data_test['Open'].astype(np.int8)

print('Normalize data set ...')
min_max_scaler = preprocessing.MinMaxScaler()
data_store['CompetitionDistance'] = min_max_scaler.fit_transform(data_store['CompetitionDistance'])

print('Create ultimate data')
# this is concatenating datasets including info from stores
data_ut_store = pd.merge(data_mean, data_store, on='Store')
data_ut_train = pd.merge(data_train,data_ut_store, on='Store')
data_ut_test  = pd.merge(data_test,data_ut_store, on='Store')

print data_ut_train[0:1]
print ('...')
print data_store[0:1]
print ('...')

assert( len( data_ut_train ) == len( data_train ))
assert( len( data_ut_test ) == len( data_test ))

print('Storing data ...')
hdf = HDFStore(data_dir + 'data.h5')
hdf.put('data_train', data_ut_train, format='table', data_columns=True)
hdf.put('data_test', data_ut_test, format='table', data_columns=True)
hdf.put('data_store', data_ut_store, format='table', data_columns=True)

print('Done ...')
