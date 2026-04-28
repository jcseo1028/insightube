/**
 * InSighTube 클라이언트 스크립트
 */

document.addEventListener("DOMContentLoaded", () => {
    const urlInput = document.getElementById("url-input");

    // 입력 필드 클릭 시 클립보드에서 YouTube URL 자동 붙여넣기
    urlInput?.addEventListener("focus", async () => {
        if (urlInput.value) return; // 이미 값이 있으면 무시

        try {
            const text = await navigator.clipboard.readText();
            if (text && isYouTubeUrl(text)) {
                urlInput.value = text;
                urlInput.select();
            }
        } catch {
            // 클립보드 권한 없으면 무시
        }
    });
});

/**
 * YouTube URL 여부를 간단히 검증한다.
 * @param {string} url - 검증할 URL
 * @returns {boolean}
 */
function isYouTubeUrl(url) {
    return /(?:youtube\.com\/watch\?.*v=|youtu\.be\/|youtube\.com\/embed\/)/.test(url);
}

/**
 * 오늘의 독서 내용 팝업을 새 창으로 연다.
 * 팝업 차단 회피를 위해 사용자 클릭 핸들러 내에서 직접 호출되어야 한다.
 */
function openReadingToday() {
    const features = "width=720,height=820,resizable=yes,scrollbars=yes";
    window.open("/reading/today", "insightube_reading", features);
}
