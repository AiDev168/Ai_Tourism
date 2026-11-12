"""Offline assistant API contract: no network, database or paid calls."""
from datetime import UTC, datetime
from uuid import UUID, uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import SecretStr

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
            'idempotency_key': 'assistant-0001', 'expected_version': 1,
            'remote_processing_consent': True}


def test_explicit_consent_and_disabled_gateway_do_not_reserve():
    c, repo, gateway = client()
    try:
        bad = body()
        bad['remote_processing_consent'] = False
        assert c.post(f'/api/v1/conversations/{CONV}/assistant-turns', json=bad).status_code == 422
        assert repo.calls == 0 and not gateway.calls
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


def test_assistant_candidate_uses_trip_contract_and_only_accepts_exact_source_spans():
    text = 'می‌خواهم چند روز از تهران به شیراز سفر کنم و hiking دوست دارم'
    candidate = _candidate_profile(text, 'fa-IR', {
        'destination': 'شیراز', 'origin': 'تهران', 'interest': 'hiking',
    }, {'destination': 'شیراز', 'origin': 'تهران', 'interest': 'hiking'})
    assert candidate.contract_version == 'trip-requirements-v1'
    assert candidate.original_text == text
    assert candidate.fields.destination.value == 'شیراز'
    assert candidate.fields.destination.source == 'traveler'
    assert candidate.fields.origin.source == 'llm'
    assert candidate.fields.origin.value == 'تهران'
    assert candidate.fields.origin.source == 'llm'
    assert candidate.fields.duration_days.status == 'missing'
    assert candidate.fields.interests.value == ['hiking']
    assert candidate.fields.interests.source == 'llm'
    assert candidate.fields.destination.evidence_span.text == 'شیراز'


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
