"""add notification pipeline (outbox + recipients)

Revision ID: 6813df31bc67
Revises: d8b2114a1c79
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy_utc
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6813df31bc67'
down_revision: Union[str, Sequence[str], None] = 'd8b2114a1c79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # notifications: 어떤 이벤트가 이 알림을 만들었는지 추적하기 위한 컬럼 추가
    op.add_column('notifications', sa.Column('event_type', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_index(op.f('ix_notifications_event_type'), 'notifications', ['event_type'], unique=False)

    # notification_recipients: 알림 1건을 실제로 받는 회원별 수신함(읽음 상태 포함)
    op.create_table('notification_recipients',
    sa.Column('created_at', sqlalchemy_utc.sqltypes.UtcDateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sqlalchemy_utc.sqltypes.UtcDateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('deleted_at', sqlalchemy_utc.sqltypes.UtcDateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('notification_id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('read_at', sqlalchemy_utc.sqltypes.UtcDateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['notification_id'], ['notifications.id'], ),
    sa.ForeignKeyConstraint(['member_id'], ['members.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('notification_id', 'member_id', name='uq_notification_recipient_member')
    )
    op.create_index(op.f('ix_notification_recipients_notification_id'), 'notification_recipients', ['notification_id'], unique=False)
    op.create_index(op.f('ix_notification_recipients_member_id'), 'notification_recipients', ['member_id'], unique=False)

    # outbox_events: Transactional Outbox — 도메인 트랜잭션과 함께 커밋되는 발행 대기열
    op.create_table('outbox_events',
    sa.Column('created_at', sqlalchemy_utc.sqltypes.UtcDateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sqlalchemy_utc.sqltypes.UtcDateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('deleted_at', sqlalchemy_utc.sqltypes.UtcDateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('dispatched', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('dispatched_at', sqlalchemy_utc.sqltypes.UtcDateTime(timezone=True), nullable=True),
    sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_outbox_events_event_type'), 'outbox_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_outbox_events_dispatched'), 'outbox_events', ['dispatched'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_outbox_events_dispatched'), table_name='outbox_events')
    op.drop_index(op.f('ix_outbox_events_event_type'), table_name='outbox_events')
    op.drop_table('outbox_events')

    op.drop_index(op.f('ix_notification_recipients_member_id'), table_name='notification_recipients')
    op.drop_index(op.f('ix_notification_recipients_notification_id'), table_name='notification_recipients')
    op.drop_table('notification_recipients')

    op.drop_index(op.f('ix_notifications_event_type'), table_name='notifications')
    op.drop_column('notifications', 'event_type')
