from datetime import timedelta, datetime, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") #비밀번호 해쉬화

def password_hash(password: str) -> str:
    return pwd_context.hash(password)
#사용자가 입력한 password값이랑 DB의 hash된 password값이 같은지 검증
#hash된 password를 다시 복호화하지 않는 이유는
#해시 알고리즘은 임의의 길이 데이터를 고정된 길이의 고유한 데이터(해시 값)로 변환하는 단방향 암호화 기술이기 때문이다.
#plain_password: 사용자가 로그인할 때 입력한 해시되지 않은 비밀번호.
#bool 타입으로 리턴 이유: 2개의 문자가 같은지 verify를 하면 같다/아니다의 값으로만 나오기 때문이다.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

#jwt access_token
#expires_delta: timedelta = 시간 간격(기간)을 표현하는 타입(언제부터 언제까지 몇십분동안 유효하다..)
def create_access_token(data: str, expires_delta: timedelta | None = None) -> str:
    #if expires_delta is not None 에서 is not None 생략
    #특수하게 유효기간을 지정해야할 시
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    #expires_delta가 none일 시 .env에 지정한 Access token minutes=30을 적용
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)

    #jwt 안에 숨겨놓은 데이터 지정
    to_encode: dict[str, Any] = {
        "sub": data,
        "type": "access",
        "exp": expire,
    }

    #jwt에는 인자가 3개 들어감
    #1. 숨겨놓을 데이터, 2. 복호화할 때 쓸 비밀키, 3. 암호화 할 알고리즘
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# jwt refresh_token
def create_refresh_token(data: str, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    #refresh 토큰은 오래가야 하기 때문에 minutes가 아닌 days로 함.
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_DAYS)

    # jwt 안에 숨겨놓은 데이터 지정
    to_encode: dict[str, Any] = {
        "sub": data,
        "type": "refresh",
        "exp": expire,
    }

    # jwt에는 인자가 3개 들어감
    # 1. 숨겨놓을 데이터, 2. 복호화할 때 쓸 비밀키, 3. 암호화 할 알고리즘
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)