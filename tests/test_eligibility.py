"""Shared eligibility logic tests.

These lock down the behavior that used to differ between room_scheduler and
dispatch_builder before both were rewritten to call
automation_hub.eligibility.evaluate_room for every decision.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from automation_hub.dispatch_builder import build_dispatch_plan
from automation_hub.eligibility import evaluate_room, resolve_room_expression
from automation_hub.rooms import AutomationRoom, RoomRegistry
from automation_hub.room_scheduler import build_plan
from automation_hub.workflow_contracts import (
    load_contracts,
    validate_channel_groups,
    validate_contract_expressions,
)

KST = ZoneInfo("Asia/Seoul")
NOW = datetime(2026, 8, 24, 10, 0, tzinfo=KST)  # Monday

WP_CONTRACT = {
    "daily-network-publish.yml": {
        "platforms": ["wordpress"],
        "mode": "workflow_dispatch",
        "inputs": {
            "room_id": "room.room_id",
            "target_site_url": "room.name_url",
            "publication_approved": False,
        },
        "required_inputs": ["room_id", "target_site_url"],
        "safe_policy": "draft",
        "artifact_kind": "wordpress_post_id",
    }
}

YT_CONTRACT = {
    "generate-youtube-playlist.yml": {
        "platforms": ["youtube"],
        "mode": "workflow_dispatch",
        "channel_groups": ["PLAYLIST"],
        "inputs": {"room_id": "room.room_id", "channel": "room.account_id"},
        "required_inputs": ["room_id", "channel"],
        "safe_policy": "private",
        "artifact_kind": "youtube_video_id",
    }
}

BLOGGER_MANAGED_CONTRACT = {
    "blogger-daily-scheduler.yml": {
        "platforms": ["blogger"],
        "mode": "scheduler_managed",
        "inputs": {},
        "required_inputs": [],
        "safe_policy": "draft",
        "artifact_kind": "blogger_draft_id",
    }
}


def _wp_room(**overrides) -> AutomationRoom:
    base = dict(
        room_id="wp_test", platform="wordpress", name="example.com",
        enabled=True, workflow="daily-network-publish.yml",
        publish_policy="draft", duplicate_guard=True,
    )
    base.update(overrides)
    return AutomationRoom.from_dict(base)


def _yt_room(**overrides) -> AutomationRoom:
    base = dict(
        room_id="yt_test", platform="youtube", name="Test Channel",
        enabled=True, workflow="generate-youtube-playlist.yml",
        destination_id="UC0000000000000000000000",
        group="PLAYLIST", publish_policy="private", duplicate_guard=True,
    )
    base.update(overrides)
    return AutomationRoom.from_dict(base)


# ---- WordPress URL normalization -------------------------------------------------

def test_wordpress_url_is_normalized_to_https():
    room = _wp_room(name="bare-domain.com")
    assert resolve_room_expression("room.name_url", room) == "https://bare-domain.com"


def test_wordpress_url_left_alone_when_already_a_scheme():
    room = _wp_room(name="http://already-has-scheme.com")
    assert resolve_room_expression("room.name_url", room) == "http://already-has-scheme.com"


# ---- disabled / duplicate_guard / policy mismatch / schedule window --------------

def test_disabled_room_is_excluded():
    room = _wp_room(enabled=False)
    result = evaluate_room(room, WP_CONTRACT, NOW)
    assert not result.eligible
    assert result.reason == "disabled"


def test_duplicate_guard_off_is_excluded():
    room = _wp_room(duplicate_guard=False)
    result = evaluate_room(room, WP_CONTRACT, NOW)
    assert not result.eligible
    assert result.reason == "duplicate_guard_off"


def test_policy_mismatch_is_excluded_and_awaiting_approval_cannot_bypass_it():
    # A WordPress-family room claiming awaiting_approval must NOT slip through
    # just because that string is a valid safe_policy somewhere else (Tistory).
    room = _wp_room(publish_policy="awaiting_approval")
    result = evaluate_room(room, WP_CONTRACT, NOW)
    assert not result.eligible
    assert result.reason == "policy_mismatch"


def test_schedule_window_outside_allowed_hours_is_excluded():
    room = _wp_room(schedule_policy={"allowed_hours": [1, 2, 3]})
    result = evaluate_room(room, WP_CONTRACT, NOW)
    assert not result.eligible
    assert result.reason == "outside_schedule_window"


def test_schedule_window_wrong_weekday_is_excluded():
    # NOW is a Monday (weekday()==0); restrict to Sunday (6) only.
    room = _wp_room(schedule_policy={"weekdays": [6]})
    result = evaluate_room(room, WP_CONTRACT, NOW)
    assert not result.eligible
    assert result.reason == "outside_schedule_window"


def test_next_run_in_future_is_excluded():
    room = _wp_room(next_run="2099-01-01T00:00:00+09:00")
    result = evaluate_room(room, WP_CONTRACT, NOW)
    assert not result.eligible
    assert result.reason == "next_run_in_future"


def test_next_run_in_past_is_allowed_through():
    room = _wp_room(next_run="2020-01-01T00:00:00+09:00")
    result = evaluate_room(room, WP_CONTRACT, NOW)
    assert result.eligible


def test_missing_destination_excludes_remote_platforms():
    room = _yt_room(destination_id="")
    result = evaluate_room(room, YT_CONTRACT, NOW)
    assert not result.eligible
    assert result.reason == "missing_destination"


# ---- required_inputs --------------------------------------------------------------

def test_required_input_empty_is_excluded():
    # room.name_url resolves empty when name is blank -> target_site_url required_input fails.
    room = _wp_room(name="")
    result = evaluate_room(room, WP_CONTRACT, NOW)
    assert not result.eligible
    assert result.reason == "required_input_empty:target_site_url"


def test_youtube_channel_required_input_resolves_from_youtube_registry():
    # Real destination_id from config/youtube_channels.json should resolve
    # room.account_id -> channel_key even though the room itself has no
    # account_id set, instead of failing required_inputs.
    room = _yt_room(destination_id="UCbJfEtsffpgI5MsKkB7BYvQ")  # globalmusic
    result = evaluate_room(room, YT_CONTRACT, NOW)
    assert result.eligible
    assert result.inputs["channel"] == "globalmusic"


def test_youtube_channel_required_input_empty_when_unresolvable():
    room = _yt_room(destination_id="UCunknownunknownunknown0")
    result = evaluate_room(room, YT_CONTRACT, NOW)
    assert not result.eligible
    assert result.reason == "required_input_empty:channel"


# ---- channel_groups ----------------------------------------------------------------

def test_channel_group_mismatch_is_excluded():
    room = _yt_room(group="KNOWLEDGE")  # contract only allows PLAYLIST
    result = evaluate_room(room, YT_CONTRACT, NOW)
    assert not result.eligible
    assert result.reason == "channel_group_mismatch"


def test_real_registry_channel_groups_all_match_their_contracts():
    registry = RoomRegistry.load()
    contracts = load_contracts()
    assert validate_channel_groups(registry, contracts) == {}


# ---- unknown room.* expression -------------------------------------------------------

def test_unknown_room_expression_is_rejected_by_dispatch():
    bad_contract = {
        "daily-network-publish.yml": {
            **WP_CONTRACT["daily-network-publish.yml"],
            "inputs": {"room_id": "room.room_id", "secret": "room.secret_token"},
            "required_inputs": ["room_id"],
        }
    }
    room = _wp_room()
    result = evaluate_room(room, bad_contract, NOW)
    assert not result.eligible
    assert result.reason == "unsupported_room_expression:room.secret_token"


def test_unknown_room_expression_is_rejected_by_static_contract_validator():
    bad_contracts = {
        "some-workflow.yml": {
            "platforms": ["wordpress"],
            "inputs": {"secret": "room.secret_token"},
        }
    }
    problems = validate_contract_expressions(bad_contracts)
    assert "some-workflow.yml" in problems


def test_real_contracts_use_only_supported_room_expressions():
    assert validate_contract_expressions(load_contracts()) == {}


# ---- scheduler_managed rooms (Blogger) never get a generic dispatch payload --------

def test_scheduler_managed_room_has_no_generic_dispatch_inputs():
    room = AutomationRoom.from_dict(dict(
        room_id="blogger_test", platform="blogger", name="test",
        enabled=True, destination_id="123", workflow="blogger-daily-scheduler.yml",
        publish_policy="draft", duplicate_guard=True,
    ))
    result = evaluate_room(room, BLOGGER_MANAGED_CONTRACT, NOW)
    assert result.eligible
    assert result.mode == "scheduler_managed"
    assert result.inputs == {}


def test_scheduler_managed_room_is_not_in_generic_dispatch_list():
    registry = RoomRegistry([
        AutomationRoom.from_dict(dict(
            room_id="blogger_test", platform="blogger", name="test",
            enabled=True, destination_id="123", workflow="blogger-daily-scheduler.yml",
            publish_policy="draft", duplicate_guard=True,
        ))
    ])
    plan = build_dispatch_plan(registry, now=NOW)
    assert plan["dispatches"] == []
    assert len(plan["scheduler_managed"]) == 1
    assert plan["scheduler_managed"][0]["room_id"] == "blogger_test"


# ---- YouTube payload can never request PUBLIC --------------------------------------

def test_youtube_dispatch_payload_cannot_request_public():
    room = _yt_room(destination_id="UCbJfEtsffpgI5MsKkB7BYvQ")
    result = evaluate_room(room, YT_CONTRACT, NOW)
    assert result.eligible
    assert "public" not in {str(v).lower() for v in result.inputs.values()}
    assert room.publish_policy == "private"


def test_publication_approved_is_always_forced_false_even_if_room_tries_true():
    contract = {
        "daily-network-publish.yml": {
            **WP_CONTRACT["daily-network-publish.yml"],
            "inputs": {**WP_CONTRACT["daily-network-publish.yml"]["inputs"], "publication_approved": True},
        }
    }
    room = _wp_room()
    result = evaluate_room(room, contract, NOW)
    assert result.eligible
    assert result.inputs["publication_approved"] is False


# ---- room_scheduler and dispatch_builder must agree ---------------------------------

def test_scheduler_and_dispatch_builder_select_the_same_rooms():
    registry = RoomRegistry.load()
    plan = build_plan(registry, now=NOW)
    dispatch = build_dispatch_plan(registry, now=NOW)

    scheduler_selected = {row["room_id"] for row in plan["selected"]}
    dispatch_selected = {e["room_id"] for e in dispatch["dispatches"]} | {
        e["room_id"] for e in dispatch["scheduler_managed"]
    }
    assert scheduler_selected == dispatch_selected


def test_dispatch_builder_with_scheduler_plan_matches_dispatch_builder_alone(tmp_path):
    import json

    registry = RoomRegistry.load()
    plan = build_plan(registry, now=NOW)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    direct = build_dispatch_plan(registry, now=NOW)
    via_plan = build_dispatch_plan(registry, now=NOW, plan_path=plan_path)
    assert direct["summary"] == via_plan["summary"]
