#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import datetime as dt

# read in data
data = pd.read_csv("quotedata.dat", skiprows=2)


#  Set Rate
from bs4 import BeautifulSoup as bs4
import requests

url = 'https://www.treasury.gov/resource-center/data-chart-center/interest-rates/Pages/TextView.aspx?data=yield'
req = requests.get(url)
soup = bs4(req.text, 'html.parser')
# the one month t-bill rate
table = soup.find_all('tr', attrs=({'class':"oddrow"}))
RATE = float(table[-1].find_all('td')[1].text) / 100


#  Set time-NOW. Leave as '2020-03-23 16:00:00.000000' for proof of concept
# NOW = dt.datetime.now()
NOW = pd.to_datetime('2020-03-23 16:00:00.000000')
# set _nearest date limit
_near_date = NOW + dt.timedelta(days=23)
# set farthest date limit
next_date = NOW + dt.timedelta(days=37)


#  Filtering
def filter_quotes(input_data):

    # select columns
    input_data = input_data[['Expiration Date', 'Strike', 'Calls', 'Bid', 'Ask', 'Puts', 'Bid.1', 'Ask.1']]
    # filter to between _near and next data
    input_data = input_data.loc[(pd.to_datetime(input_data['Expiration Date']) > _near_date) & (pd.to_datetime(input_data['Expiration Date']) < next_date)]
    # convert expiration date column to datetime
    input_data['Expiration Date'] = pd.to_datetime(input_data['Expiration Date'])
    # select only friday expiries
    input_data = input_data.loc[pd.DatetimeIndex(input_data['Expiration Date']).weekday == 4]

    return input_data


def filter_non_zero_bids(input_data):
    return input_data.loc[(input_data['Bid'] != 0) & (input_data['Bid.1'] != 0)]


def filter_weeklies(input_data):

    mod = input_data.loc[~input_data.Calls.str.contains('W')]
    input_data = mod if len(mod) != 0 else input_data

    return input_data


#  Datetime changes
def set_datetime(input_data):

    # had to create new datetime column to replace use of Expiration Date

    # set time for weekly expiries
    input_data['ExpDT'] = input_data.loc[input_data.Calls.str.contains('W')]['Expiration Date'] + dt.timedelta(hours=16)
    # set time for standard expiries
    input_data.loc[input_data.ExpDT.isna(), 'ExpDT'] = input_data.loc[input_data.ExpDT.isna()]['Expiration Date'] + dt.timedelta(hours=9.5)

    return input_data


def set_minutes_remaining(input_data, MINUTES_IN_YEAR):

    # set time to expiration in minutes ... input_data.ExpDT - NOW returns datetime[ns]
    input_data['TTE'] = (((input_data.ExpDT - NOW) / pd.np.timedelta64(1, 'm')) / MINUTES_IN_YEAR).values

    return input_data


#  Split Near & Next DataFrames
def split_near_next(input_data):

    data = input_data.copy()
    data = data.set_index('Expiration Date')
    #  get unique dates, will sort correctly
    dates = [str(i.date()) for i in data.index.unique()]
    #  set _nearest date
    _near = data.loc[data.index == dates[0]]
    # set next date
    _next = data.loc[data.index == dates[1]]

    return _next.reset_index(), _near.reset_index()


#  Preprocessing for VIX Calc
def set_cp_midpoints(input_data):

    input_data['calls_midpoint'] = (input_data['Ask'] + input_data['Bid']) / 2
    input_data['puts_midpoint'] = (input_data['Ask.1'] + input_data['Bid.1']) / 2
    input_data['difference'] = abs(input_data['calls_midpoint'] - input_data['puts_midpoint'])

    return input_data


def set_F(input_data, RATE):

    strike = input_data.loc[input_data.index == (input_data.loc[input_data.difference == input_data.difference.min()].index[0])]['Strike']
    call = input_data.loc[input_data.index == (input_data.loc[input_data.difference == input_data.difference.min()].index[0])]['calls_midpoint']
    put = input_data.loc[input_data.index == (input_data.loc[input_data.difference == input_data.difference.min()].index[0])]['puts_midpoint']
    tte = input_data.loc[input_data.index == (input_data.loc[input_data.difference == input_data.difference.min()].index[0])]['TTE']
    _F = strike + np.exp(tte * RATE) * (call - put)

    return _F.values[0]


def set_K0(input_data, F):
    return input_data.loc[input_data.Strike < F].iloc[-1]['Strike']


def set_deltaK(input_data):
    return ((input_data.Strike.shift(-1) - input_data.Strike.shift(1)) / 2).values


def set_Ki_squared(input_data):
    return (input_data.Strike ** 2).values


def set_deltaK_dividedby_KiSqrd(input_data):
    return (input_data.deltaK / input_data.Ki_sqrd).values


def set_eRT(input_data, RATE):
    return np.exp(input_data.TTE.values * RATE)


def set_QKi(input_data, some_strike_K0):

    # create single midpoint column, assigning calls midpoint immediately
    input_data['midpoint'] = (input_data.Strike >= some_strike_K0) * input_data.calls_midpoint
    # assign puts midpoint
    input_data.loc[input_data.Strike < some_strike_K0 , 'midpoint'] = input_data.loc[input_data.Strike < some_strike_K0]['puts_midpoint'].values
    # average the call and put midpoint for K0
    input_data.loc[input_data.Strike == some_strike_K0 , 'midpoint'] = np.mean(input_data.loc[input_data.Strike == some_strike_K0]['puts_midpoint'].values + input_data.loc[input_data.Strike == some_strike_K0]['calls_midpoint'].values)

    return input_data


#  Implement Preprocessing
def prepare_quotes(input_data, RATE, MINUTES_IN_YEAR):

    #  filter for _near & next, friday expiries, non-zero bids
    mod = filter_quotes(input_data)
    #  create new expiration date column to display time
    mod = set_datetime(mod)
    #  create time to expiry in minutes
    mod = set_minutes_remaining(mod, MINUTES_IN_YEAR)
    #  set index
    mod = mod.reset_index()
    mod = mod.drop('index', axis=1)
    #  get midpoint
    mod = set_cp_midpoints(mod)

    #  split
    _next, _near = split_near_next(mod)

    # filter weeklies
    _near = filter_weeklies(_near)
    _next = filter_weeklies(_next)

    #  F Forward index level derived from index option prices
    F1 = set_F(_near, RATE)
    F2 = set_F(_next, RATE)

    # Set K0
    _near_K0 = set_K0(_near, F1)
    _next_K0 = set_K0(_next, F2)

    # set Q(K_i)
    _near = set_QKi(_near, _near_K0)
    _next = set_QKi(_next, _next_K0)

    # set delta K
    _near['deltaK'] = set_deltaK(_near)
    _next['deltaK'] = set_deltaK(_next)

    # set K_i ** 2
    _near['Ki_sqrd'] = set_Ki_squared(_near)
    _next['Ki_sqrd'] = set_Ki_squared(_next)

    # set deltaK / Ki^2
    _near['delK_div_KiSqrd'] = set_deltaK_dividedby_KiSqrd(_near)
    _next['delK_div_KiSqrd'] = set_deltaK_dividedby_KiSqrd(_next)

    # set e^rt
    _near['eRT'] = set_eRT(_near, RATE)
    _next['eRT'] = set_eRT(_next, RATE)

    # filter non zero bids
    _near = filter_non_zero_bids(_near)
    _next = filter_non_zero_bids(_next)

    return _next, _near


#  Final Preprocessing
def set_d1(input_data):
    return ((2/input_data.TTE.values[0]) * np.sum(input_data.delK_div_KiSqrd * input_data.eRT * input_data.midpoint))


def set_d2(input_data, F, K0):
    return ((1/input_data.TTE.values[0]) * ((F / K0)  - 1) ** 2)


def set_sigma(d1, d2):
    return d1 - d2


def calc_sigma(input_data, RATE):

    _F = set_F(input_data, RATE)
    _K0 = set_K0(input_data, _F)
    _d1 = set_d1(input_data)
    _d2 = set_d2(input_data, _F, _K0)
    _sigma = set_sigma(_d1, _d2)

    return _sigma


#  Calculate VIX
def calc_vix(input_data_from_dat_file, RATE, NOW):

    MINUTES_IN_YEAR = 525600

    _next, _near = prepare_quotes(data, RATE, MINUTES_IN_YEAR)

    _next_sigma = calc_sigma(_next, RATE)

    _near_sigma = calc_sigma(_near, RATE)

    # set t1
    t1 = _near.TTE.iloc[0]
    # set t2
    t2 = _next.TTE.iloc[0]
    # number of minutes in year
    n365 = MINUTES_IN_YEAR
    # number of minutes in 30 days
    n30 = 43200
    # number of minutes till settlement for _near
    nt1 = (_next.ExpDT.iloc[0] - NOW).total_seconds() / 60
    # number of minutes till settlement for next
    nt2 = (_near.ExpDT.iloc[0] - NOW).total_seconds() / 60

    _near_weight = t1 * _near_sigma * ((nt2 - n30) / (nt2 - nt1))
    next_weight = t2 * _next_sigma * ((n30 - nt1) / (nt2 - nt1))
    weighted_values = (_near_weight + next_weight) * (n365/n30)

    vix = 100 * np.sqrt(weighted_values)

    return vix


if __name__ == '__main__':

    VIX = calc_vix(data, RATE, NOW)
    print()
    print(f'VIX: {VIX}')
    print()
