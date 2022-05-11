# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Carolina Giménez Escalante
# All rights reserved.
#

from reports.requests.entrypoint import generate


def test_requests(progress, client_factory, response_factory, ff_request, asset):
    responses = []

    parameters = {
        "date": {
            "after": "2021-01-01T00:00:00",
            "before": "2021-12-01T00:00:00",
        },
        "product": {
            "all": True,
            "choices": [],
        },
        "marketplace": {
            "all": True,
            "choices": [],
        },
        "rr_type": {
            "all": True,
            "choices": [],
        },
        "connexion_type": {
            "all": False,
            "choices": ["production"],
        },
    }
    responses.append(
        response_factory(
            count=2,
        ),
    )

    responses.append(
        response_factory(
            query='and(in(status,(approved)), '
                  'ge(start_date,2021-01-01T00:00:00),le(start_date,2021-12-01T00:00:00),'
                  'in(connexion_type,(production)))',
            value=[ff_request],
        ),
    )
    responses.append(
        response_factory(
            query='and(in(asset.id,(''AS-1895-0864-1238'')))',
            value=[asset],
        ),
    )

    client = client_factory(responses)

    result = list(generate(client, parameters, progress))

    assert len(result) == 0
