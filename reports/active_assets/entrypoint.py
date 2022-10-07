# -*- coding: utf-8 -*-
#
# Copyright (c) 2022, CloudBlue GCSPdM
# All rights reserved.

import datetime
from http import client
import re
from connect.client import R
import requests


from ..utils import convert_to_datetime, get_basic_value, get_value, today_str

FOREXAPI_URL = 'https://theforexapi.com/api/latest'
BASE_CURRENCY = 'USD'

HEADERS = (
    'assetId', 'assetStatus', 'externalId' , 'productId', 'providerId', 'providerName', 'marketplaceId','marketplaceName', 'contractId', 'contractName', 'resellerId',
    'resellerExternalId', 'resellerName', 'createdAt', 'customerId', 'customerExternalId', 'customerName', 'seamlessMove', 'discountGroup',
    'action','renewalDate', 'purchaseType', 'adobeCustomerId', 'adobeVIPNumber', 'adobeUserEmail', 'currency','cost', 'resellerCost', 'msrp','seats',
    'USDCost', 'USDMsrp', 'USDResellerCost'
)

def generate(
    client=None,
    parameters=None,
    progress_callback=None,
    renderer_type=None,
    extra_context_callback=None,
):
    """
    Extracts data from Connect using the ConnectClient instance
    and input data provided as arguments, applies
    required transformations (if any) and returns the data rendered
    by the given renderer on the arguments list.
    Some renderers may require extra context data to generate the report
    output, for example in the case of the Jinja2 renderer...

    :param client: An instance of the CloudBlue Connect
                    client.
    :type client: cnct.ConnectClient
    :param input_data: Input data used to calculate the
                        resulting dataset.
    :type input_data: dict
    :param progress_callback: A function that accepts t
                                argument of type int that must
                                be invoked to notify the progress
                                of the report generation.
    :type progress_callback: func
    :param renderer_type: Renderer required for generating report
                            output.
    :type renderer_type: string
    :param extra_context_callback: Extra content required by some
                            renderers.
    :type extra_context_callback: func
    """
    assets = _get_assets(client, parameters)
    price_list_points_DB = {}
    progress = 0
    total = assets.count()
    if renderer_type == 'csv':
        yield HEADERS
        progress += 1
        total += 1
        progress_callback(progress, total)

    for asset in assets:
        if asset['marketplace']['id'] not in price_list_points_DB:
            price_list_points_DB[asset['marketplace']['id']] = _fill_marketplace_pricelist(client, asset['marketplace']['id'], asset['product']['id'])
        yield _process_line(asset, price_list_points_DB[asset['marketplace']['id']])
        progress += 1
        progress_callback(progress, total)


def _get_assets(client, parameters):
    status = ['active']
    environment = 'production'

    query = R()
    if parameters.get('date') and parameters['date']['after'] != '':
        query &= R().events.created.at.ge(parameters['date']['after'])
        query &= R().events.created.at.le(parameters['date']['before'])
    if parameters.get('product') and parameters['product']['all'] is False:
        query &= R().product.id.oneof(parameters['product']['choices'])
    query &= R().status.oneof(status)
    query &= R().connection.type.eq(environment)

    return client('subscriptions').assets.filter(query)

def _process_line(asset, marketplace_price_list_points):
    seamless_move, discount, action, renewal_date_parameter, adobe_customer_id, adobe_vip_number, adobe_user_email = _process_asset_parameters(asset['params'])
    renewal_date = _calculate_renewal_date(renewal_date_parameter, asset['events']['created']['at'], action)
    asset_type, currency, cost, reseller_cost, msrp, seats = _get_asset_type_financials_and_seats_number(asset['items'], marketplace_price_list_points, asset['product']['id'])
    base_currency_cost, base_currency_reseller_cost, base_currency_msrp = _get_base_currency_financials(cost, reseller_cost, msrp, marketplace_price_list_points)
    return (
        get_basic_value(asset ,'id'),
        get_basic_value(asset ,'status'),
        get_basic_value(asset ,'external_id'),
        get_basic_value(asset['product'], 'id'),
        get_value(asset['connection'], 'provider', 'id'),
        get_value(asset['connection'], 'provider', 'name'),
        get_basic_value(asset['marketplace'], 'id'),
        get_basic_value(asset['marketplace'], 'name'),
        get_basic_value(asset['contract'], 'name'),
        get_basic_value(asset['contract'], 'name'),
        get_value(asset['tiers'], 'tier1', 'id'),
        get_value(asset['tiers'], 'tier1', 'external_id'),
        get_value(asset['tiers'], 'tier1', 'name'),
        convert_to_datetime(
            get_value(asset['events'], 'created', 'at'),
        ),
        get_value(asset['tiers'], 'customer', 'id'),
        get_value(asset['tiers'], 'customer', 'external_id'),
        get_value(asset['tiers'], 'customer', 'name'),
        seamless_move,
        discount,
        action,
        renewal_date,
        asset_type,
        adobe_customer_id,
        adobe_vip_number,
        adobe_user_email,
        currency,
        '{:0.2f}'.format(cost),
        '{:0.2f}'.format(reseller_cost),
        '{:0.2f}'.format(msrp),
        seats,
        '{:0.2f}'.format(base_currency_cost),
        '{:0.2f}'.format(base_currency_reseller_cost),
        '{:0.2f}'.format(base_currency_msrp),
    )

def _process_asset_parameters(asset_parameters):
    seamless_move = '-'
    discount = '-'
    action = '-'
    adobe_customer_id = '-'
    adobe_vip_number = '-'
    adobe_user_email = '-'
    renewal_date = '-'
    for assetParam in asset_parameters:
        if assetParam['id'] == 'seamless_move':
            seamless_move = assetParam['value']
        elif assetParam['id'] == 'discount_group':
            if assetParam['value'] == '01A12':
                discount = 'Level 1'
            elif assetParam['value'] == '02A12':
                discount = 'Level 2'
            elif assetParam['value'] == '03A12':
                discount = 'Level 3'
            elif assetParam['value'] == '04A12':
                discount = 'Level 4'
            elif assetParam['value'] == '01012':
                discount = 'TLP Level 1'
            elif assetParam['value'] == '02012':
                discount = 'TLP Level 2'
            elif assetParam['value'] == '03012':
                discount = 'TLP Level 3'
            elif assetParam['value'] == '04012':
                discount = 'TLP Level 4'
            elif assetParam['value'] == '':
                discount = 'Empty'
            else:
                discount = 'Other'
        elif assetParam['id'] == 'action_type':
            action = assetParam['value']
        elif assetParam['id'] == 'renewal_date':
            renewal_date = assetParam['value']
        elif assetParam['id'] == 'adobe_customer_id' and assetParam['value'] != '':
            adobe_customer_id = assetParam['value']
        elif assetParam['id'] == 'adobe_vip_number' and assetParam['value'] != '':
            adobe_vip_number = assetParam['value']
        elif assetParam['id'] == 'adobe_user_email' and assetParam['value'] != '':
            adobe_user_email = assetParam['value']
    return seamless_move, discount, action, renewal_date, adobe_customer_id, adobe_vip_number, adobe_user_email


def _calculate_renewal_date(renewal_date_parameter, asset_creation_date, action):
    if action == 'purchase' or renewal_date_parameter == '-' or renewal_date_parameter == '' or '/' not in renewal_date_parameter:  # Net new, dates set by asset. Second validation n case the report is executed for a non-Adobe product, making sure it does nto fail
        if datetime.datetime.now(datetime.timezone.utc) < (datetime.datetime.fromisoformat(asset_creation_date) + datetime.timedelta(days = 365)):
            renewal_date = datetime.datetime.fromisoformat(asset_creation_date) + datetime.timedelta(days = 365)
        else:
            renewal_date = datetime.datetime.fromisoformat(asset_creation_date).replace(year = (datetime.datetime.now(datetime.timezone.utc).year + 1))
    else:  # Transfer, use parameter value
        if '/' in renewal_date_parameter:
            regex = re.match('(.*)/(.*)/(.*)', renewal_date_parameter)
            renewal_date_parameter = regex.group(3) + '-' + regex.group(2) + '-' + regex.group(1)
        if datetime.datetime.now(datetime.timezone.utc) < (datetime.datetime.fromisoformat(renewal_date_parameter).replace(tzinfo=datetime.timezone.utc) + datetime.timedelta(days = 365)):
            renewal_date = datetime.datetime.fromisoformat(renewal_date_parameter).replace(tzinfo=datetime.timezone.utc) + datetime.timedelta(days = 365)
        else:
            renewal_date = datetime.datetime.fromisoformat(renewal_date_parameter).replace(tzinfo=datetime.timezone.utc).replace(year = (datetime.datetime.now(datetime.timezone.utc).year + 1))

    return renewal_date.strftime("%Y-%m-%d %H:%M:%S")

def _fill_marketplace_pricelist(client, marketplace_id, product_id):
    marketplace_price_list = {}
    listing_query = R()
    listing_query &= R().marketplace.id.eq(marketplace_id)
    listing_query &= R().product.id.eq(product_id)
    listing_query &= R().status.eq('listed')
    listing = client.listings.filter(listing_query).first()
    if listing and 'pricelist' in listing and listing['pricelist']['status'] == 'active':
        pricelist_id = listing['pricelist']['id']
        price_list_version_query = R()
        price_list_version_query &= R().pricelist.id.eq(pricelist_id)
        price_list_version_query &= R().status.eq('active')
        price_list_version = client('pricing').versions.filter(price_list_version_query).first()
        marketplace_price_list['currency'] = price_list_version['pricelist']['currency']
        if marketplace_price_list['currency'] == BASE_CURRENCY:
            marketplace_price_list['FX'] = 1
        else:
            exchange_params = {'base': marketplace_price_list['currency'], 'symbols': BASE_CURRENCY}
            exchange_request = requests.get(FOREXAPI_URL, params = exchange_params)
            if exchange_request.status_code == requests.codes.ok:
                if BASE_CURRENCY in exchange_request.json()['rates']:
                    marketplace_price_list['FX'] = float(exchange_request.json()['rates'][BASE_CURRENCY])
                else:
                    marketplace_price_list['FX'] = 0
            else:
                marketplace_price_list['FX'] = 0
        price_list_version_points = client('pricing').versions[price_list_version['id']].points.all()
        for price_list_version_point in price_list_version_points:
            if float(price_list_version_point['attributes']['price']) != 0:
                if 'pricepoints' not in marketplace_price_list:
                    marketplace_price_list['pricepoints'] = {}
                if product_id not in marketplace_price_list['pricepoints']:
                    marketplace_price_list['pricepoints'][product_id] = {}
                if price_list_version_point['id'] not in marketplace_price_list['pricepoints'][product_id]:
                    marketplace_price_list['pricepoints'][product_id][price_list_version_point['id']] = {}
                marketplace_price_list['pricepoints'][product_id][price_list_version_point['id']]['cost'] = float(price_list_version_point['attributes']['price'])
                marketplace_price_list['pricepoints'][product_id][price_list_version_point['id']]['resellerCost'] = float(price_list_version_point['attributes']['st0p']) if 'st0p' in price_list_version_point['attributes'] else 0.0
                marketplace_price_list['pricepoints'][product_id][price_list_version_point['id']]['msrp'] = float(price_list_version_point['attributes']['st1p'])
        return marketplace_price_list
    else: # Listing has no pricelist or is not active
        return None

def _get_asset_type_financials_and_seats_number(asset_items, marketplace_price_list_points, product_id):
    asset_type = '-'
    currency = '-'
    cost = 0
    reseller_cost = 0
    msrp = 0
    seats = 0
    if marketplace_price_list_points and len(marketplace_price_list_points) > 0:
        currency = marketplace_price_list_points['currency']
        for item in asset_items:
            if 'Enterprise' in item['display_name'] and asset_type == '-':
                asset_type = 'enterprise'
            elif 'Enterprise' in item['display_name'] and asset_type == 'team':
                asset_type = 'both'
            else:
                asset_type = 'team'
            if int(item['quantity']) > 0:
                seats = seats + int(item['quantity'])
                if 'pricepoints' in marketplace_price_list_points and len(marketplace_price_list_points['pricepoints'][product_id]) > 0:
                    if item['global_id'] in marketplace_price_list_points['pricepoints'][product_id]:
                        cost = cost + int(item['quantity']) * float(marketplace_price_list_points['pricepoints'][product_id][item['global_id']]['cost'])
                        msrp = msrp + int(item['quantity']) * float(marketplace_price_list_points['pricepoints'][product_id][item['global_id']]['msrp'])
                        reseller_cost = reseller_cost + int(item['quantity']) * float(marketplace_price_list_points['pricepoints'][product_id][item['global_id']]['resellerCost'])

    return asset_type, currency, cost, reseller_cost, msrp, seats

def _get_base_currency_financials(cost, reseller_cost, msrp, marketplace_price_list_points):
    base_currency_cost = 0
    base_currency_reseller_cost = 0
    base_currency_msrp = 0
    if marketplace_price_list_points and len(marketplace_price_list_points) > 0:
        base_currency_cost = cost * marketplace_price_list_points['FX']
        base_currency_reseller_cost = reseller_cost * marketplace_price_list_points['FX']
        base_currency_msrp = msrp * marketplace_price_list_points['FX']
    return base_currency_cost, base_currency_reseller_cost, base_currency_msrp
