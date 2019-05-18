import json
import logging
from enum import Enum

from flask import Blueprint, Response, request
from injector import inject

from core import domain
from core.analyser import TweetAnalyser
from core.domain import SubjectType, Serializable

bp = Blueprint('api', __name__)


def js(data):
    return json.dumps(data, sort_keys=True, indent=4, cls=Encoder)


@inject
@bp.route("/api/all", defaults={'subj_type': SubjectType.ALL})
@bp.route("/api/all/<subj_type>")
def all_data(db: domain.Database, subj_type):
    subjects = db.subjects

    try:
        if type(subj_type) is str:
            subj_type = SubjectType[subj_type.upper()]
    except Exception as e:
        logging.exception(e)
        return Response("{'error':'Bad subject type.'}", status=400, mimetype='application/json')

    t10 = subjects.top(10, 'desc', subj_type=subj_type)
    b10 = subjects.top(10, subj_type=subj_type)
    hot = subjects.hot(10, subj_type=subj_type, sort='desc')
    trend = subjects.trend(10, subj_type=subj_type, sort='desc', trend_time=2)

    return js({'top10': t10, 'bottom10': b10, 'hot10': hot, 'trend10': trend})


@inject
@bp.route("/api/summaries")
def summaries(db: domain.Database):
    subjects = db.subjects

    days = request.args.get('days', default=7, type=int)            # Last 'n' days of summaries
    limit = request.args.get('limit', default=10, type=int)         # How many subjects (per day) to retrieve
    sort = request.args.get('sort', default='desc', type=str)       # Direction of sort; asc or desc.
    at_least = request.args.get('at_least', default=1, type=int)    # Minimum number of tweets on a subject

    summaries_raw = subjects.summaries(days=days, limit=limit, sort=sort, at_least=at_least)

    response_map = {}

    for row in summaries_raw:
        if row.day not in response_map:
            response_map[row.day] = []

        response_map[row.day].append(row)

    return js({"content": response_map, "meta": {"size": len(summaries_raw)}})


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name

        if isinstance(obj, Serializable):
            return obj.to_dict()

        return json.JSONEncoder.encode(self, obj)


@bp.route("/api/loc")
def location(ta: TweetAnalyser):
    return js(ta.locations_arr)
