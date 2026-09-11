// 공용 인증 fetch 래퍼
// access token 만료(401) 시, refresh token으로 자동 재발급 후 원 요청을 1회 재시도한다.
// 각 페이지의 기존 fetch 호출을 바꿀 필요 없이, window.fetch를 감싸서 전역 적용한다.
(function () {
    const origFetch = window.fetch.bind(window);
    let reissuePromise = null;   // 동시 다발 401에서 재발급을 1번만 수행하기 위한 락

    function urlOf(input) {
        return typeof input === 'string' ? input : (input && input.url) || '';
    }

    async function reissueOnce() {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) return false;
        try {
            const res = await origFetch('/members/reissue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });
            if (!res.ok) return false;
            const tokens = await res.json();   // TokenOut (감싸지 않은 직접 객체)
            if (!tokens.access_token) return false;
            localStorage.setItem('access_token', tokens.access_token);
            if (tokens.refresh_token) localStorage.setItem('refresh_token', tokens.refresh_token);
            return true;
        } catch (e) {
            return false;
        }
    }

    window.fetch = async function (input, init = {}) {
        const res = await origFetch(input, init);
        const url = urlOf(input);

        // 401이 아니거나, 인증 엔드포인트 자체(재발급/로그인)면 그대로 반환
        if (res.status !== 401 || url.includes('/members/reissue') || url.includes('/members/login')) {
            return res;
        }

        // 401 → 재발급 (여러 요청이 동시에 401이면 재발급은 1번만)
        if (!reissuePromise) {
            reissuePromise = reissueOnce().finally(() => { reissuePromise = null; });
        }
        const ok = await reissuePromise;

        if (!ok) {
            // 재발급 실패(리프레시도 만료 등) → 로그아웃 후 로그인 페이지로
            localStorage.clear();
            if (!location.pathname.endsWith('/login.html')) {
                location.href = '/static/login.html';
            }
            return res;
        }

        // 새 access token으로 Authorization 교체 후 원 요청 1회 재시도
        const retryInit = Object.assign({}, init);
        retryInit.headers = Object.assign({}, init.headers || {}, {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        });
        return origFetch(input, retryInit);
    };
})();
