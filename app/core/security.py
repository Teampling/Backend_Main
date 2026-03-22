from passlib.context import CryptContext

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

