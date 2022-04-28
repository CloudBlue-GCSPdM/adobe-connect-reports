# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Carolina Giménez Escalante
# All rights reserved.
#

from connect.client.rql import R
from reports.utils import (get_value, get_basic_value, convert_to_datetime, today_str)

HEADERS = ['Request ID', 'Connect Subscription ID', 'End Customer Subscription ID',
           'Adobe Order #', 'Adobe Transfer ID #', 'VIP #', 'Adobe Cloud Program ID',
           'Pricing SKU Level (Volume Discount level)',
           'End Customer External ID', 'Provider  ID', 'Provider Name',
           'Marketplace', 'Product ID', 'Product Name', 'Subscription Status',
           'Effective Date', 'Creation Date', 'Connect Order Type', 'Connection Type', 'Exported At']


def generate(client, parameters, progress_callback, renderer_type=None, extra_context=None, ):
    requests = _get_requests(client, parameters)

    progress = 0
    total = requests.count() + 1

    for request in requests:
        order_number = ''
        transfer_number = ''
        vip_number = ''
        adobe_cloud_program_id = ''
        pricing_level = ''

        # get subscription parameters values
        for param in request['asset']['params']:
            if 'adobe_vip_number' == get_basic_value(param, 'id'):
                vip_number = get_basic_value(param, 'value')
            if 'adobe_order_id' == get_basic_value(param, 'id'):
                order_number = get_basic_value(param, 'value')
            if 'transfer_id' == get_basic_value(param, 'id'):
                transfer_number = get_basic_value(param, 'value')

        if pricing_level == '01A12':
            pricing_level = 'Level 1'
        elif pricing_level == '02A12':
            pricing_level = 'Level 2'
        elif pricing_level == '03A12':
            pricing_level = 'Level 3'
        elif pricing_level == '04A12':
            pricing_level = 'Level 4'
        elif pricing_level == '01012':
            pricing_level = 'TLP Level 1'
        elif pricing_level == '02012':
            pricing_level = 'TLP Level 2'
        elif pricing_level == '03012':
            pricing_level = 'TLP Level 3'
        elif pricing_level == '04012':
            pricing_level = 'TLP Level 4'
        elif pricing_level == '':
            pricing_level = 'Empty'

        subscription = _get_subscription(client, request['asset']['id'])
        if subscription.count() > 0:
            for param in subscription.first()['params']:
                if 'adobe_customer_id' == get_basic_value(param, 'id'):
                    adobe_cloud_program_id = get_basic_value(param, 'value')
                if 'discount_group' == get_basic_value(param, 'id'):
                    pricing_level = get_basic_value(param, 'value')

        if progress == 0:
            yield HEADERS
            progress += 1
            total += 1
            progress_callback(progress, total)

        yield (
            get_basic_value(request, 'id'),  # Request ID
            get_value(request, 'asset', 'id'),  # Connect Subscription ID
            get_value(request, 'asset', 'external_id'),  # End Customer Subscription ID
            order_number,  # Adobe Order #
            transfer_number,  # Adobe Transfer ID #
            vip_number,  # VIP #
            adobe_cloud_program_id,  # Adobe Cloud Program ID
            pricing_level,  # Pricing SKU Level (Volume Discount level)
            get_value(request['asset']['tiers'], 'customer', 'external_id'),  # End Customer External ID
            get_value(request['asset']['connection'], 'provider', 'id'),  # Provider ID
            get_value(request['asset']['connection'], 'provider', 'name'),  # Provider Name
            get_value(request, 'marketplace', 'name'),  # Marketplace
            get_value(request['asset'], 'product', 'id'),  # Product ID
            get_value(request['asset'], 'product', 'name'),  # Product Name
            get_value(request, 'asset', 'status'),  # Subscription Status
            convert_to_datetime(
                get_basic_value(request, 'effective_date'),  # Effective  Date
            ),
            convert_to_datetime(
                get_basic_value(request, 'created'),  # Creation  Date
            ),
            get_basic_value(request, 'type'),  # Transaction Type,
            get_basic_value(request['asset']['connection'], 'type'),  # Connection Type,
            today_str(),  # Exported At
        )
        progress += 1
        progress_callback(progress, total)


def _get_requests(client, parameters):
    status = ['approved']

    query = R()
    query &= R().status.oneof(status)
    query &= R().created.ge(parameters['date']['after'])
    query &= R().created.le(parameters['date']['before'])

    if parameters.get('connexion_type') and parameters['connexion_type']['all'] is False:
        query &= R().asset.connection.type.oneof(parameters['connexion_type']['choices'])

    if parameters.get('product') and parameters['product']['all'] is False:
        query &= R().asset.product.id.oneof(parameters['product']['choices'])
    if parameters.get('rr_type') and parameters['rr_type']['all'] is False:
        query &= R().type.oneof(parameters['rr_type']['choices'])
    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        query &= R().marketplace.id.oneof(parameters['mkp']['choices'])

    return client.requests.filter(query).order_by("created")


def _get_subscription(client, asset_id):
    query = R()
    query &= R().id.oneof([asset_id])

    return client.ns('subscriptions').assets.filter(query)
