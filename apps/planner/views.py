from __future__ import annotations

import json

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from .engine import generate_plan_from_payload
from .payloads import sample_payload_dict


def planner_home(request: HttpRequest) -> HttpResponse:
    return render(request, "planner/index.html", {"initial_payload": sample_payload_dict()})


def planner_api(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    try:
        if "application/json" in (request.content_type or ""):
            data = json.loads(request.body.decode("utf-8") or "{}")
        else:
            data = request.POST.dict()

        payload_text = json.dumps(
            {
                "subjects": data.get("subjects") or [],
                "config": data.get("config") or {},
            }
        )
        result = generate_plan_from_payload(payload_text, data.get("start") or None)
        return JsonResponse(
            {
                "plan": result.blocks_payload,
                "tips": result.coaching_tips,
            }
        )
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)
