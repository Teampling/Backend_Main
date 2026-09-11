import socket
import uuid

NOTIFICATION_STREAM_NAME = "notifications:stream"   # 이벤트가 흐르는 Redis Stream 키 (relay·consumer 공유 계약)
NOTIFICATION_GROUP_NAME = "notification-workers"    # Consumer Group 이름 (consumer 공유 계약)
OUTBOX_POLL_INTERVAL_SECONDS = 1.0                  # relay가 outbox를 다시 폴링하기까지 대기(초)
OUTBOX_BATCH_SIZE = 100                             # relay가 한 번에 처리할 미발행 outbox 행 수
CONSUMER_NAME = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"   # 그룹 내 컨슈머 식별자 (인스턴스마다 유일)
CONSUMER_READ_COUNT = 10                            # 한 번 XREADGROUP에서 최대 몇 개 읽을지
CONSUMER_BLOCK_MS = 5000                            # 새 메시지 없을 때 최대 대기 시간(ms)
NOTIFICATION_CHANNEL_PREFIX = "notify:"             # 실시간 Pub/Sub 채널 접두사 (publish/subscribe 공유 계약, notify:{member_id})