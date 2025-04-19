import pytest
from unittest.mock import AsyncMock, patch
from services import deal_notifier

@pytest.mark.asyncio
@patch("services.deal_notifier.get_deal_photos", return_value=["img1.png", "img2.png"])
@patch("senders.telegram.send_telegram_media_group")
async def test_notify_deal_complete(mock_send, mock_get):
    mock_send.return_value = AsyncMock()

    data = {
        "stage_id": "WON",
        "deal_id": "123"
    }
    await deal_notifier.notify_deal_complete(data)

    mock_get.assert_called_once_with("123")
    mock_send.assert_called_once_with(chat_id=int(os.getenv("TG_CHAT_ID")), media_paths=["img1.png", "img2.png"])
