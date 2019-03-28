from flask import Blueprint, Response
from injector import inject
import logging
import json

from core import domain
from core.analyser import TweetAnalyser
from core.domain import SubjectType

bp = Blueprint('api', __name__)


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

    return json.dumps({'top10': t10, 'bottom10': b10, 'hot10': hot})


@bp.route("/api/loc")
def location(ta: TweetAnalyser):
    return json.dumps(ta.locations_arr)
