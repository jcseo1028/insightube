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
