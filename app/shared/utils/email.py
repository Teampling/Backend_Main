import random
import string
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.core.redis import redis_client

async def send_email(subject: str, recipient: str, body: str):
    """
    aiosmtplib를 사용하여 이메일을 비동기로 발송합니다.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"SMTP 설정이 없어 이메일을 발송하지 않았습니다. [To: {recipient}, Code/Body: {body}]")
        return

    message = MIMEMultipart()
    message["From"] = settings.EMAIL_FROM
    message["To"] = recipient
    message["Subject"] = subject

    # HTML 형식으로 보낼 수도 있으므로 plain 대신 html을 선택적으로 사용할 수 있게 확장 가능
    message.attach(MIMEText(body, "plain"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,
        )
    except Exception as e:
        print(f"이메일 발송 중 오류 발생: {str(e)}")
        # 실제 운영 환경에서는 로거를 사용하세요.

def generate_verification_code(length: int = 6) -> str:
    """
    지정된 길이의 랜덤 숫자 코드를 생성합니다.
    """
    return "".join(random.choices(string.digits, k=length))

async def send_verification_email(
    email: str, 
    code: str, 
    purpose: str = "signup", 
    custom_message: str | None = None
):
    """
    인증 코드를 포함한 이메일을 발송하고 Redis에 저장합니다.
    
    :param email: 수신자 이메일
    :param code: 6자리 인증 코드
    :param purpose: 인증 목적 (예: signup, reset_password)
    :param custom_message: 이메일 본문에 포함할 커스텀 메시지
    """
    # Redis에 저장 (key format: "verify:{purpose}:{email}", TTL: 5분(300초))
    redis_key = f"verify:{purpose}:{email}"
    await redis_client.setex(redis_key, 300, code)

    # 이메일 제목 및 본문 설정
    subjects = {
        "signup": "[Teampling] 회원가입 인증 코드입니다.",
        "reset_password": "[Teampling] 비밀번호 재설정 인증 코드입니다.",
        "common": "[Teampling] 인증 코드입니다."
    }
    subject = subjects.get(purpose, subjects["common"])

    if custom_message:
        body = f"{custom_message}\n\n인증 코드: {code}\n\n이 코드는 5분 동안 유효합니다."
    else:
        body = f"요청하신 인증 코드는 다음과 같습니다.\n\n인증 코드: {code}\n\n이 코드는 5분 동안 유효합니다."

    await send_email(subject, email, body)

async def verify_code(email: str, code: str, purpose: str = "signup") -> bool:
    """
    Redis에 저장된 코드와 입력된 코드가 일치하는지 확인합니다.
    """
    redis_key = f"verify:{purpose}:{email}"
    stored_code = await redis_client.get(redis_key)
    
    if stored_code and stored_code == code:
        # 인증 성공 시 코드 삭제 (1회용 인증)
        await redis_client.delete(redis_key)
        return True
    return False
