"""Offline assistant API contract: no network, database or paid calls."""
from datetime import UTC, date, datetime
from uuid import UUID, uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

from app.api.assistant import _candidate_profile, get_assistant_turn_repository, get_chat_gateway
from app.api.auth import require_authenticated_csrf
from app.api.traveler import get_traveler_repository
from app.core.config import Settings, get_settings
from app.modules.identity.authorization import Principal, get_principal
from app.modules.integrations.chat_adapter import ChatReply
from app.modules.trip.assistant_turns import TurnReservation
from app.modules.trip.requirements_interpretation import interpret_trip_requirements

OWNER = UUID('9d6c521e-6d84-4a8c-b463-e0fe5a2dc0d1')
OTHER = uuid4()
CONV = uuid4()
TRIP = uuid4()
TURN = uuid4()
USER_MSG = uuid4()
ASSISTANT_MSG = uuid4()


class FakeChatRepo:
    def __init__(self):
        self.calls = 0
        self.status = 'reserved'
        self.last = None
        self.finished = None

    def reserve(self, **kwargs):
        self.calls += 1
        self.last = kwargs
        if kwargs['user_id'] != OWNER:
            from app.modules.trip.repository import TravelerNotFound
            raise TravelerNotFound
        return TurnReservation(TURN, self.status, 'fa-IR', USER_MSG, ASSISTANT_MSG, self.status == 'reserved' and not getattr(self, 'is_replay', False))

    def budget_status(self, **kwargs):
        return {'user_used': 2, 'user_remaining': kwargs['per_user_limit'] - 2,
                'user_limit': kwargs['per_user_limit'], 'global_used': 11,
                'global_remaining': kwargs['global_limit'] - 11,
                'global_limit': kwargs['global_limit']}

    def history(self, **kwargs):
        assert kwargs['user_id'] == OWNER
        return [{'role': 'user', 'content': 'سفر سه روزه'}]

    def complete(self, **kwargs):
        self.finished = kwargs

    def fail(self, **kwargs):
        self.failed = kwargs

    def result(self, **kwargs):
        return {'message_id': ASSISTANT_MSG, 'conversation_id': CONV, 'trip_id': TRIP,
                'role': 'assistant', 'content': 'کدام شهر را ترجیح می‌دهید؟',
                'created_at': datetime.now(UTC),
                'metadata': {'requirements_candidate': (
                    self.finished.get('requirements', {}) if self.finished
                    else {'duration_days': 3}
                ),
                             'clarification': 'مقصد؟'}}


class FakeTraveler:
    def conversation(self, user_id, conversation_id):
        now = datetime.now(UTC)
        return {'conversation_id': CONV, 'locale': 'fa-IR', 'version': 3,
                'started_at': now, 'updated_at': now, 'last_message_at': now,
                'trips': [self.trip(user_id, TRIP)], 'messages': [
                    {'message_id': ASSISTANT_MSG, 'conversation_id': CONV,
                     'trip_id': TRIP, 'role': 'assistant',
                     'content': 'کدام شهر را ترجیح می‌دهید؟', 'created_at': now},
                ]}

    def trip(self, user_id, trip_id):
        now = datetime.now(UTC)
        return {'trip_id': TRIP, 'conversation_id': CONV, 'version': 2,
                'locale': 'fa-IR', 'original_request': 'سفر سه روزه',
                'extracted_requirements': {}, 'confirmed_requirements': {},
                'destination_ids': [], 'duration_days': 3, 'traveler_count': None,
                'budget_amount_original': None, 'budget_currency_iso': None,
                'budget_unit': None, 'latest_recommendation_request_id': None,
                'latest_itinerary_id': None, 'trip_status': 'draft',
                'created_at': now, 'updated_at': now}


class FakeGateway:
    def __init__(self):
        self.calls = []

    async def invoke(self, request):
        self.calls.append(request)
        return ChatReply(reply='کدام شهر را ترجیح می‌دهید؟',
                         requirements={'duration_days': 3}, clarification='مقصد؟')


def client(owner=OWNER, enabled=True):
    repo, traveler, gateway = FakeChatRepo(), FakeTraveler(), FakeGateway()
    settings = Settings(_env_file=None, database_password='test', app_env='test',
                        internal_chat_enabled=enabled,
                        internal_chat_endpoint='https://example.invalid/v1/chat/completions',
                        internal_chat_model='fixture', internal_chat_token=SecretStr('test')) if enabled else Settings(
                            _env_file=None, database_password='test', app_env='test')
    # Import the real API under explicit offline test settings. No .env needed.
    with patch('app.core.config.get_settings', return_value=settings):
        from app.main import app
    app.dependency_overrides[get_principal] = lambda: Principal(owner, uuid4())
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_assistant_turn_repository] = lambda: repo
    app.dependency_overrides[get_traveler_repository] = lambda: traveler
    app.dependency_overrides[get_chat_gateway] = lambda: gateway
    return TestClient(app), repo, gateway


def body():
    return {'trip_id': str(TRIP), 'content': 'لطفاً برنامه سفر بده',
            'idempotency_key': 'assistant-0001', 'expected_version': 1}


def test_authenticated_chat_does_not_require_redundant_ai_consent_checkbox():
    c, repo, gateway = client()
    try:
        result = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=body())
        assert result.status_code == 200, result.text
        assert repo.calls == 1 and len(gateway.calls) == 1
    finally:
        c.app.dependency_overrides.clear()
    c, repo, gateway = client(enabled=False)
    try:
        assert c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=body()).status_code == 503
        assert repo.calls == 0 and not gateway.calls
    finally:
        c.app.dependency_overrides.clear()


def test_conversation_api_returns_five_key_typed_assistant_candidate():
    c, _, _ = client()
    traveler = c.app.dependency_overrides[get_traveler_repository]()
    original_conversation = traveler.conversation
    candidate = interpret_trip_requirements("Plan a trip to Shiraz", "en-US").model_dump(mode="json")

    def with_candidate(user_id, conversation_id):
        result = original_conversation(user_id, conversation_id)
        result["messages"][0]["candidate_requirements"] = candidate
        return result

    traveler.conversation = with_candidate
    try:
        response = c.get(f"/api/v1/conversations/{CONV}")
        assert response.status_code == 200
        returned = response.json()["messages"][0]["candidate_requirements"]
        assert returned["contract_version"] == "trip-requirements-v1"
        assert len(returned) == 5
    finally:
        c.app.dependency_overrides.clear()


def test_authenticated_turn_persists_candidate_without_confirming_it():
    c, repo, gateway = client()
    try:
        result = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=body())
        assert result.status_code == 200, result.text
        assert result.headers['cache-control'] == 'no-store'
        candidate = result.json()['candidate_requirements']
        assert candidate['contract_version'] == 'trip-requirements-v1'
        assert candidate['fields']['duration_days']['status'] == 'missing'
        assert result.json()['trip']['confirmed_requirements'] == {}
        assert repo.last['user_id'] == OWNER and repo.finished['turn_id'] == TURN
        assert len(gateway.calls) == 1
        assert gateway.calls[0].history[0].content == 'سفر سه روزه'
    finally:
        c.app.dependency_overrides.clear()


def test_model_provisional_itinerary_is_returned_and_replayed_without_provider_retry():
    c, repo, gateway = client()
    itinerary = {
        'status': 'provisional_unverified',
        'days': [{'day_number': 1, 'stops': [{'name': 'Eram Garden', 'role': 'model_proposed'}]}],
    }

    async def response(request):
        gateway.calls.append(request)
        return ChatReply(reply='Draft only; verify details before travel.', provisional_itinerary=itinerary)

    gateway.invoke = response
    original_result = repo.result

    def result(**kwargs):
        value = original_result(**kwargs)
        value['metadata']['provisional_itinerary'] = repo.finished.get('provisional_itinerary')
        return value

    repo.result = result
    try:
        first = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=body())
        assert first.status_code == 200, first.text
        assert first.json()['provisional_itinerary'] == itinerary
        assert repo.finished['provisional_itinerary'] == itinerary
        assert first.json()['candidate_requirements']['original_text'] == body()['content']
        assert first.json()['extraction_path'] == 'fallback'
        repo.status = 'completed'
        repo.is_replay = True
        replay = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=body())
        assert replay.status_code == 200, replay.text
        assert replay.json()['replayed'] is True
        assert replay.json()['provisional_itinerary'] == itinerary
        assert len(gateway.calls) == 1
    finally:
        c.app.dependency_overrides.clear()


def test_assistant_turn_exposes_llm_extraction_path_and_typed_current_turn_evidence():
    c, repo, gateway = client()
    text = "\u0627\u0632 \u0645\u0634\u0647\u062f \u0645\u06cc\u062e\u0648\u0627\u0645 \u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632"

    async def response(request):
        gateway.calls.append(request)
        return ChatReply(
            reply='\u0628\u0631\u0627\u06cc \u0686\u0646\u062f \u0631\u0648\u0632 \u0645\u06cc\u200c\u0631\u0648\u06cc\u062f\u061f',
            requirements={'origin': '\u0645\u0634\u0647\u062f', 'destination': '\u0634\u06cc\u0631\u0627\u0632'},
            requirement_evidence={'origin': text, 'destination': text},
        )

    gateway.invoke = response
    request_body = body() | {'content': text}
    try:
        result = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=request_body)
        assert result.status_code == 200, result.text
        candidate = result.json()['candidate_requirements']
        assert result.json()['extraction_path'] == 'llm'
        assert candidate['original_text'] == text
        assert candidate['fields']['origin']['value'] == '\u0645\u0634\u0647\u062f'
        assert candidate['fields']['destination']['value'] == '\u0634\u06cc\u0631\u0627\u0632'
        assert candidate['fields']['origin']['source'] == 'llm'
        assert candidate['fields']['origin']['evidence_span']['text'] == text
        assert repo.finished['requirements']['fields']['origin']['value'] == '\u0645\u0634\u0647\u062f'
    finally:
        c.app.dependency_overrides.clear()


def test_assistant_turn_reuses_saved_local_date_context_without_server_clock():
    c, _, gateway = client()
    traveler = c.app.dependency_overrides[get_traveler_repository]()
    original_trip = traveler.trip
    saved = interpret_trip_requirements(
        '\u0645\\0646 \u0641\u0631\u062f\u0627 \u0628\u0631\u0645', 'fa-IR',
        traveler_timezone='Asia/Tehran', traveler_reference_date=date(2026, 11, 15),
    ).model_dump(mode='json')

    def trip_with_calendar_context(user_id, trip_id):
        value = original_trip(user_id, trip_id)
        value['extracted_requirements'] = {
            '_traveler_context': {'timezone': 'Asia/Tehran', 'reference_date': '2026-11-20'},
            'requirements_v1': saved,
        }
        return value

    traveler.trip = trip_with_calendar_context
    text = '\u0641\u0631\u062f\u0627 \u0628\u0631\u0645'
    async def response(request):
        gateway.calls.append(request)
        return ChatReply(
            reply='Please confirm the duration.',
            requirements={'relative_start_date': 1},
            requirement_evidence={'relative_start_date': text},
        )

    gateway.invoke = response
    try:
        result = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=body() | {'content': text})
        assert result.status_code == 200, result.text
        assert gateway.calls[0].traveler_timezone == 'Asia/Tehran'
        assert gateway.calls[0].traveler_reference_date == date(2026, 11, 20)
        relative = result.json()['candidate_requirements']['fields']['relative_start_date']
        assert relative['value']['anchor_date'] == '2026-11-21'
        assert relative['value']['timezone'] == 'Asia/Tehran'
    finally:
        c.app.dependency_overrides.clear()


def test_initial_persisted_request_can_be_reused_as_the_first_ai_turn():
    c, repo, gateway = client()
    request = body()
    request['existing_user_message_id'] = str(USER_MSG)
    try:
        result = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=request)
        assert result.status_code == 200, result.text
        assert repo.last['existing_user_message_id'] == USER_MSG
        assert len(gateway.calls) == 1
        assert gateway.calls[0].text == request['content']
    finally:
        c.app.dependency_overrides.clear()


def test_assistant_status_reports_configuration_and_budget_without_invocation():
    c, repo, gateway = client()
    try:
        result = c.get('/api/v1/assistant/status')
        assert result.status_code == 200
        assert result.headers['cache-control'] == 'no-store'
        assert result.json() == {
            'state': 'configured', 'user_used': 2, 'user_remaining': 6,
            'user_limit': 8, 'global_used': 11, 'global_remaining': 89,
            'global_limit': 100,
        }
        assert gateway.calls == [] and repo.calls == 0
    finally:
        c.app.dependency_overrides.clear()


def test_assistant_candidate_uses_trip_contract_and_only_accepts_exact_source_spans():
    text = 'می‌خواهم چند روز از تهران به مناطق تاریخی شیراز سفر کنم و hiking دوست دارم'
    candidate = _candidate_profile(text, 'fa-IR', {
        'destination': 'شیراز', 'origin': 'تهران', 'interest': 'hiking',
    }, {'destination': 'شیراز', 'origin': 'تهران', 'interest': 'hiking'})
    assert candidate.contract_version == 'trip-requirements-v1'
    assert candidate.original_text == text
    assert candidate.fields.destination.value == 'شیراز'
    assert candidate.fields.destination.source == 'llm'
    assert candidate.fields.origin.source == 'llm'
    assert candidate.fields.origin.value == 'تهران'
    assert candidate.fields.origin.source == 'llm'
    assert candidate.fields.duration_days.status == 'missing'
    assert candidate.fields.interests.value == ['historical_attractions', 'hiking']
    assert candidate.fields.interests.source == 'llm'
    assert candidate.fields.destination.evidence_span.text == 'شیراز'


@pytest.mark.parametrize("text", [
    "\u0627\u0632 \u0645\u0634\u0647\u062f \u0645\u06cc\u062e\u0648\u0627\u0645 \u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632",
    "\u0645\u06cc\u200c\u062e\u0648\u0627\u0645 \u0627\u0632 \u0645\u0634\u0647\u062f \u0631\u0627\u0647\u06cc \u0634\u06cc\u0631\u0627\u0632 \u0628\u0634\u0645",
    "\u0645\u0646 \u0627\u0632 \u0645\u0634\u0647\u062f \u0645\u06cc\u062e\u0648\u0627\u0647\u0645 \u0628\u0631\u0648\u0645 \u0634\u06cc\u0631\u0627\u0632",
])
def test_llm_semantics_populate_mashhad_origin_even_when_parser_does_not(text):
    candidate = _candidate_profile(
        text, 'fa-IR', {'origin': '\u0645\u0634\u0647\u062f', 'destination': '\u0634\u06cc\u0631\u0627\u0632'},
        {'origin': text, 'destination': text},
    )
    assert candidate.original_text == text
    assert candidate.fields.origin.value == '\u0645\u0634\u0647\u062f'
    assert candidate.fields.destination.value == '\u0634\u06cc\u0631\u0627\u0632'
    assert candidate.fields.origin.source == candidate.fields.destination.source == 'llm'
    assert candidate.fields.origin.evidence_span.text == text


def test_llm_ambiguity_is_preserved_instead_of_choosing_fallback_guess():
    text = "\u0627\u0632 \u0645\u0634\u0647\u062f \u06cc\u0627 \u062a\u0628\u0631\u06cc\u0632 \u0645\u06cc\u062e\u0648\u0627\u0645 \u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632"
    candidate = _candidate_profile(text, 'fa-IR', {}, {'origin': text}, {
        'origin': ['\u0645\u0634\u0647\u062f', '\u062a\u0628\u0631\u06cc\u0632'],
    })
    assert candidate.fields.origin.status == 'ambiguous'
    assert candidate.fields.origin.candidates == ['\u0645\u0634\u0647\u062f', '\u062a\u0628\u0631\u06cc\u0632']
    assert candidate.fields.origin.source == 'llm'


def test_relative_departure_keeps_stored_traveler_anchor_and_does_not_become_duration():
    text = "\u0627\u0632 \u067e\u0633\u200c\u0641\u0631\u062f\u0627 \u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632"
    candidate = _candidate_profile(
        text, 'fa-IR', {'relative_start_date': 2}, {'relative_start_date': text},
        traveler_timezone='Asia/Tehran', traveler_reference_date=date(2026, 11, 15),
    )
    relative = candidate.fields.relative_start_date.value
    assert candidate.fields.relative_start_date.source == 'llm'
    assert relative.offset_days == 2
    assert relative.anchor_date == date(2026, 11, 17)
    assert relative.timezone == 'Asia/Tehran'
    assert candidate.fields.duration_days.status == 'missing'


def test_p0_reference_request_accepts_llm_semantics_for_all_core_fields():
    # The model supplies independently quoted field evidence. Deterministic
    # extraction is not required to recognize this sentence structure.
    text = (
        "\u0627\u0632 \u0645\u0634\u0647\u062f \u0645\u06cc\u200c\u062e\u0648\u0627\u0645 "
        "\u0627\u0632 \u067e\u0633\u200c\u0641\u0631\u062f\u0627 \u0628\u0631\u0627\u06cc "
        "\u067e\u0646\u062c \u0631\u0648\u0632 \u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632. "
        "\u067e\u0646\u062c \u0646\u0641\u0631 \u0647\u0633\u062a\u06cc\u0645 \u0648 "
        "\u0628\u0648\u062f\u062c\u0647\u200c\u0645\u0648\u0646 \u06f3\u06f0 \u0645\u06cc\u0644\u06cc\u0648\u0646 "
        "\u062a\u0648\u0645\u0646\u0647. \u0628\u06cc\u0634\u062a\u0631 \u062c\u0627\u0647\u0627\u06cc "
        "\u062a\u0627\u0631\u06cc\u062e\u06cc \u0648 \u0628\u0627\u063a\u200c\u0647\u0627 \u0631\u0648 "
        "\u062f\u0648\u0633\u062a \u062f\u0627\u0631\u06cc\u0645."
    )
    evidence = {
        'origin': "\u0627\u0632 \u0645\u0634\u0647\u062f",
        'destination': "\u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632",
        'relative_start_date': "\u0627\u0632 \u067e\u0633\u200c\u0641\u0631\u062f\u0627",
        'duration_days': "\u0628\u0631\u0627\u06cc \u067e\u0646\u062c \u0631\u0648\u0632",
        'traveler_count': "\u067e\u0646\u062c \u0646\u0641\u0631 \u0647\u0633\u062a\u06cc\u0645",
        'budget_text': "\u06f3\u06f0 \u0645\u06cc\u0644\u06cc\u0648\u0646 \u062a\u0648\u0645\u0646\u0647",
        'interest': "\u062c\u0627\u0647\u0627\u06cc \u062a\u0627\u0631\u06cc\u062e\u06cc \u0648 \u0628\u0627\u063a\u200c\u0647\u0627",
    }
    candidate = _candidate_profile(
        text, 'fa-IR', {
            'origin': '\u0645\u0634\u0647\u062f', 'destination': '\u0634\u06cc\u0631\u0627\u0632',
            'relative_start_date': 2, 'duration_days': 5, 'traveler_count': 5,
            'budget_text': evidence['budget_text'],
            'interest': evidence['interest'],
        }, evidence, traveler_timezone='Asia/Tehran',
        traveler_reference_date=date(2026, 11, 15),
    )
    assert candidate.original_text == text
    assert candidate.fields.origin.value == '\u0645\u0634\u0647\u062f'
    assert candidate.fields.destination.value == '\u0634\u06cc\u0631\u0627\u0632'
    assert candidate.fields.relative_start_date.value.anchor_date == date(2026, 11, 17)
    assert candidate.fields.duration_days.value == 5
    assert candidate.fields.travelers.value == 5
    budget = candidate.fields.budget.value
    assert (budget.amount, budget.scale, budget.currency, budget.raw) == (
        '30', 'million', 'TOMAN', evidence['budget_text'],
    )
    assert candidate.fields.interests.value == ['historical_attractions', 'gardens', evidence['interest']]
    assert all(getattr(candidate.fields, name).source == 'llm' for name in (
        'origin', 'destination', 'relative_start_date', 'duration_days',
        'travelers', 'budget', 'interests',
    ))
    assert candidate.fields.duration_days.status == 'known'


def test_llm_relative_date_overrides_a_different_deterministic_guess():
    text = 'We should leave the morning after tomorrow.'
    candidate = _candidate_profile(
        text, 'en-US', {'relative_start_date': 2}, {'relative_start_date': text},
        traveler_timezone='Asia/Tehran', traveler_reference_date=date(2026, 11, 15),
    )
    relative = candidate.fields.relative_start_date.value
    assert relative.offset_days == 2
    assert relative.anchor_date == date(2026, 11, 17)
    assert candidate.fields.relative_start_date.source == 'llm'


def test_llm_today_offset_zero_is_supported_without_inventing_reference_date():
    candidate = _candidate_profile(
        'Today, please.', 'en-US', {'relative_start_date': 0}, {'relative_start_date': 'Today'},
        traveler_timezone='Asia/Tehran', traveler_reference_date=date(2026, 11, 15),
    )
    assert candidate.fields.relative_start_date.value.offset_days == 0
    assert candidate.fields.relative_start_date.value.anchor_date == date(2026, 11, 15)


def test_llm_semantic_duration_count_and_budget_do_not_require_parser_sentence_patterns():
    text = "We'll be away for a week, traveling as a family of five; our ceiling is 5 million toman."
    candidate = _candidate_profile(
        text, 'en-US',
        {'duration_days': 7, 'traveler_count': 5, 'budget_text': '5 million toman'},
        {'duration_days': 'a week', 'traveler_count': 'family of five',
         'budget_text': '5 million toman'},
    )
    assert candidate.fields.duration_days.value == 7
    assert candidate.fields.duration_days.source == 'llm'
    assert candidate.fields.travelers.value == 5
    assert candidate.fields.travelers.source == 'llm'
    budget = candidate.fields.budget.value
    assert budget.amount == '5'
    assert budget.scale == 'million'
    assert budget.currency == 'TOMAN'
    assert budget.raw == '5 million toman'
    assert budget.currency_status == 'known'


def test_exact_quote_allows_semantic_refinement_of_a_fallback_destination():
    text = 'Not Shiraz; Tehran instead.'
    candidate = _candidate_profile(
        text, 'en-US', {'destination': 'Tehran'},
        {'destination': 'Not Shiraz; Tehran instead'},
    )
    # This remains an advisory candidate for traveler review. It does not
    # modify the saved/confirmed profile.
    assert candidate.fields.destination.value == 'Tehran'
    assert candidate.fields.destination.source == 'llm'
    assert candidate.fields.destination.evidence_span.text == 'Not Shiraz; Tehran instead'


def test_unquoted_model_candidate_cannot_replace_a_supported_parser_value():
    text = 'Plan a trip to Shiraz.'
    candidate = _candidate_profile(
        text, 'en-US', {'destination': 'Tehran'}, {'destination': 'Shiraz'},
    )
    assert candidate.fields.destination.value == 'Shiraz'
    assert candidate.fields.destination.source == 'fallback'


def test_budget_candidate_preserves_exact_unknown_currency_and_denomination():
    text = 'I want a budget of 10 million.'
    candidate = _candidate_profile(
        text, 'en-US', {'budget_text': '10 million USD'},
        {'budget_text': '10 million'},
    )
    budget = candidate.fields.budget.value
    assert budget.amount == '10'
    assert budget.scale == 'million'
    assert budget.currency is None
    assert budget.currency_status == 'unknown'
    assert budget.raw == '10 million'


def test_hard_constraint_candidate_cannot_paraphrase_traveler_safety_text():
    text = 'I cannot use stairs.'
    candidate = _candidate_profile(
        text, 'en-US', {'hard_constraint': 'stairs are inconvenient'},
        {'hard_constraint': 'cannot use stairs'},
    )
    assert candidate.fields.hard_constraints.status == 'known'
    assert candidate.fields.hard_constraints.value == ['cannot use stairs']
    assert candidate.fields.hard_constraints.source == 'fallback'


def test_explicit_soft_preference_has_a_distinct_typed_candidate():
    quote = 'ترجیح می‌دهم هتل آرام باشد'
    candidate = _candidate_profile(
        quote, 'fa-IR', {'soft_preference': quote}, {'soft_preference': quote},
    )
    assert candidate.fields.soft_preferences.status == 'known'
    fallback = interpret_trip_requirements(quote, 'fa-IR').fields.soft_preferences.value
    assert candidate.fields.soft_preferences.value == fallback
    assert len(candidate.fields.soft_preferences.value) == 1
    assert candidate.fields.soft_preferences.source == 'llm'
    assert candidate.fields.hard_constraints.status == 'missing'


def test_soft_preference_requires_explicit_preference_wording_and_cannot_be_paraphrased():
    hard_wording = 'Do not use a boat.'
    not_a_preference = _candidate_profile(
        hard_wording, 'en-US', {'soft_preference': hard_wording},
        {'soft_preference': hard_wording},
    )
    assert not_a_preference.fields.soft_preferences.status == 'missing'
    quote = 'I prefer a quiet hotel.'
    paraphrased = _candidate_profile(
        quote, 'en-US', {'soft_preference': 'a quiet hotel'},
        {'soft_preference': quote},
    )
    assert paraphrased.fields.soft_preferences.status == 'known'
    assert paraphrased.fields.soft_preferences.value == ['a quiet hotel']
    assert paraphrased.fields.soft_preferences.source == 'llm'


def test_candidate_accepts_only_an_explicit_complete_iso_date_pair():
    text = 'Please travel on 2026-12-31 and return on 2027-01-02.'
    candidate = _candidate_profile(
        text, 'en-US', {
            'travel_start': '2026-12-31', 'travel_end': '2027-01-02',
        }, {
            'travel_start': '2026-12-31', 'travel_end': '2027-01-02',
        },
    )
    assert candidate.fields.travel_dates.status == 'known'
    assert candidate.fields.travel_dates.value == {
        'start': date(2026, 12, 31), 'end': date(2027, 1, 2),
    }
    assert candidate.fields.travel_dates.source == 'llm'


def test_candidate_does_not_infer_or_accept_invalid_date_pair():
    text = 'Please travel on 2026-12-31.'
    one_endpoint = _candidate_profile(
        text, 'en-US', {'travel_start': '2026-12-31'},
        {'travel_start': '2026-12-31'},
    )
    assert one_endpoint.fields.travel_dates.status == 'missing'
    reversed_pair = _candidate_profile(
        'Return 2026-12-30 after departure 2026-12-31.', 'en-US',
        {'travel_start': '2026-12-31', 'travel_end': '2026-12-30'},
        {'travel_start': '2026-12-31', 'travel_end': '2026-12-30'},
    )
    assert reversed_pair.fields.travel_dates.status == 'missing'


@pytest.mark.parametrize(
    ('text', 'locale', 'field', 'key', 'value'),
    [
        ('4 days', 'en-US', 'duration_days', 'duration_days', 4),
        ('make it 4 days', 'en-US', 'duration_days', 'duration_days', 4),
        ('مدت سفر را ۴ روز کنید', 'fa-IR', 'duration_days', 'duration_days', 4),
        ('اجعلها أربعة أيام', 'ar', 'duration_days', 'duration_days', 4),
        ('there are five of us', 'en-US', 'travelers', 'traveler_count', 5),
        ('ما ۴ نفریم', 'fa-IR', 'travelers', 'traveler_count', 4),
        ('نحن خمسة أشخاص', 'ar', 'travelers', 'traveler_count', 5),
    ],
)
def test_numeric_candidates_accept_exact_multilingual_number_with_field_context(
    text, locale, field, key, value,
):
    candidate = _candidate_profile(
        text, locale, {key: value}, {key: text},
    )
    parsed = getattr(candidate.fields, field)
    assert parsed.status == 'known'
    assert parsed.value == value
    assert parsed.source == 'llm'
    assert parsed.evidence_span.text == text


def test_duration_correction_can_replace_only_fallback_value_with_exact_latest_evidence():
    text = 'The trip was 3 days; actually make it 4 days.'
    candidate = _candidate_profile(
        text, 'en-US', {'duration_days': 4}, {'duration_days': text},
    )
    assert candidate.fields.duration_days.value == 4
    assert candidate.fields.duration_days.source == 'llm'


def test_numeric_candidate_rejects_relative_departure_as_trip_duration_and_wrong_counts():
    relative = _candidate_profile(
        'Travel in 4 days.', 'en-US', {'duration_days': 4},
        {'duration_days': 'in 4 days'},
    )
    assert relative.fields.duration_days.status == 'missing'
    relative_word = _candidate_profile(
        'in four days', 'en-US', {'duration_days': 4},
        {'duration_days': 'in four days'},
    )
    assert relative_word.fields.duration_days.status == 'missing'
    wrong_count = _candidate_profile(
        'There are five of us.', 'en-US', {'traveler_count': 4},
        {'traveler_count': 'five of us'},
    )
    assert wrong_count.fields.travelers.status == 'missing'


def test_llm_duration_candidate_cannot_reuse_traveler_or_budget_number():
    text = (
        'Tomorrow for 5 people, I want a budget of 5 million toman '
        'to visit historical places in Shiraz.'
    )
    candidate = _candidate_profile(
        text, 'en-US', {'duration_days': 5}, {'duration_days': text},
    )
    assert candidate.fields.duration_days.status == 'missing'
    assert candidate.fields.duration_days.value is None
    assert candidate.fields.duration_days.source == 'fallback'


def test_llm_duration_candidate_cannot_reuse_relative_departure_number():
    text = 'There are five of us. We will travel in five days and have a 5 million toman budget.'
    candidate = _candidate_profile(
        text, 'en-US', {'duration_days': 5}, {'duration_days': text},
    )
    assert candidate.fields.duration_days.status == 'missing'
    assert candidate.fields.duration_days.value is None


def test_llm_duration_candidate_cannot_reuse_persian_traveler_or_budget_number():
    text = (
        '\u0628\u0631\u0627\u06cc \u0641\u0631\u062f\u0627 \u0628\u0631\u0627\u06cc 5 \u0646\u0641\u0631 '
        '\u0628\u0631\u0627\u06cc \u0628\u0627\u0632\u062f\u06cc\u062f \u0627\u0632 \u0645\u0646\u0627\u0637\u0642 '
        '\u062a\u0627\u0631\u06cc\u062e\u06cc \u0634\u06cc\u0631\u0627\u0632 \u0628\u0631\u0646\u0627\u0645\u0647 \u0631\u06cc\u0632\u06cc '
        '\u0633\u0641\u0631 \u06a9\u0646 \u0648 \u0647\u0632\u06cc\u0646\u0647 \u0627\u06cc \u06a9\u0647 \u0645\u06cc\u062e\u0648\u0627\u06cc\u0645 '
        '\u0628\u06a9\u0646\u06cc\u0645 5 \u0645\u06cc\u0644\u06cc\u0648\u0646 \u062a\u0648\u0645\u0627\u0646 \u0627\u0633\u062a'
    )
    candidate = _candidate_profile(
        text, 'fa-IR', {'duration_days': 5}, {'duration_days': text},
    )
    assert candidate.fields.duration_days.status == 'missing'
    assert candidate.fields.duration_days.value is None


def test_completed_replay_does_not_invoke_provider_again():
    c, repo, gateway = client()
    repo.status = 'completed'
    try:
        result = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=body())
        assert result.status_code == 200
        assert result.json()['replayed'] is True
        assert gateway.calls == []
    finally:
        c.app.dependency_overrides.clear()


def test_foreign_user_and_pending_turn_are_safe():
    c, repo, gateway = client(owner=OTHER)
    try:
        result = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=body())
        assert result.status_code == 404
        assert not gateway.calls
    finally:
        c.app.dependency_overrides.clear()


def test_long_history_keeps_original_trip_and_latest_correction_without_confirming_candidate():
    c, repo, gateway = client()
    history = [
        {'role': 'assistant' if index % 2 else 'user', 'content': f'older_turn_{index}'}
        for index in range(12)
    ]
    history[-1] = {
        'role': 'user',
        'content': 'Latest correction: keep 15 days and wheelchair access mandatory.',
    }
    repo.history = lambda **kwargs: history
    traveler = c.app.dependency_overrides[get_traveler_repository]()
    original_trip = traveler.trip
    traveler.trip = lambda user_id, trip_id: {
        **original_trip(user_id, trip_id),
        'original_request': 'PERSIAN_15_DAY_ORIGINAL_REQUEST',
        'duration_days': 15,
        'confirmed_requirements': {
            'duration_days': 15,
            'constraints': ['wheelchair access is mandatory'],
        },
    }

    async def respond(request):
        gateway.calls.append(request)
        return ChatReply(
            reply='A 30-day option is only a suggestion.',
            requirements={'duration_days': 30, 'traveler_count': 5},
            clarification='Should the 15-day duration remain confirmed?',
        )

    gateway.invoke = respond
    try:
        result = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=body())
        assert result.status_code == 200, result.text
        sent_history = gateway.calls[0].history
        sent_content = [message.content for message in sent_history]
        assert sent_content[0] == 'PERSIAN_15_DAY_ORIGINAL_REQUEST'
        assert sent_content.count('PERSIAN_15_DAY_ORIGINAL_REQUEST') == 1
        assert sent_content[-1] == 'Latest correction: keep 15 days and wheelchair access mandatory.'
        assert len(sent_history) == 12
        candidate = result.json()['candidate_requirements']
        assert candidate['fields']['duration_days']['status'] == 'missing'
        assert candidate['fields']['travelers']['status'] == 'missing'
        assert result.json()['trip']['duration_days'] == 15
        assert result.json()['trip']['confirmed_requirements'] == {
            'duration_days': 15,
            'constraints': ['wheelchair access is mandatory'],
        }
    finally:
        c.app.dependency_overrides.clear()
    c, repo, gateway = client()
    repo.status = 'reserved'
    repo.is_replay = True
    try:
        result = c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=body())
        assert result.status_code == 409
        assert gateway.calls == []
    finally:
        c.app.dependency_overrides.clear()
