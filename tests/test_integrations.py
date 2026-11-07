import pytest

from closer.config import Settings
from closer.integrations.gigachat import FakeLLM
from closer.integrations.sms import FakeSmsGateway, get_sms_gateway


@pytest.mark.asyncio
async def test_fake_llm_supported():
    llm = FakeLLM()
    r = await llm.classify_and_extract("логотип за 45000 рублей до конца ноября")
    assert r["supported"] is True
    assert r.get("price") == 45000


@pytest.mark.asyncio
async def test_fake_llm_unsupported():
    llm = FakeLLM()
    r = await llm.classify_and_extract("продам автомобиль")
    assert r["supported"] is False


@pytest.mark.asyncio
async def test_fake_sms():
    gw = FakeSmsGateway("+79990000000")
    mid = await gw.send_otp("+71234567890", "code 123456")
    assert mid.startswith("fake-")


def test_sms_factory_fake():
    gw = get_sms_gateway(Settings(sms_provider="fake"))
    assert isinstance(gw, FakeSmsGateway)
