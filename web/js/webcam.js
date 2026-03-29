/* ==============================================
   BioTrust - Webcam & Liveness Handler v2.4
   ==============================================

   Fixes in v2.4:
   - UI fully translated to English
   - Continuous identity guard during liveness session
   - Auto-reject if different person appears while webcam is open

   Fixes in v2.2:
   - FPS raised from 8 to 12 (more reliable blink detection over cloud latency)
   - Explicit queue guard: skip frame if previous request still in-flight
     (prevents frame pile-up at 12fps when server is slow)
   - Comment update only; all other logic from v2.1 unchanged

   Fixes in v2.1:
   - FPS raised from 4 to 8 (blink detection needs faster sampling)
   - Uses result.current_challenge.instruction for UI (not .name)
   - CSS scaleX(-1) handles mirror — backend receives raw frame
   - Robust null checks on UI elements

   FLOW:
   1. getUserMedia → video element
   2. Start liveness session (POST /api/liveness-stream/start)
   3. Capture frames at 12fps → POST /api/liveness-stream/frame/:id
   4. Update UI with challenge instruction + progress
   5. On complete/failed → POST /api/liveness-stream/complete/:id
   ============================================== */

let webcamStream = null;
let webcamVideo = null;
let isCapturing = false;
let captureInterval = null;
let currentTransactionId = null;
let isStartingLiveness = false;
let activeSessionId = null;
let activeRunId = 0;
const RPPG_DEBUG_MODE = new URLSearchParams(window.location.search).get('rppgDebug') === '1';

const IDENTITY_CHECK_INTERVAL_MS = 2000;
const MAX_IDENTITY_MISMATCHES = 2;
const NO_FACE_CANCEL_SECONDS = 5;
const LIVENESS_START_RETRYABLE_STATUS = new Set([502, 503, 504]);
const LIVENESS_START_MAX_ATTEMPTS = 3;
const LIVENESS_START_TIMEOUT_MS = 12000;

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function readResponseError(response, fallbackMessage) {
    try {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            const data = await response.json();
            return data.detail || data.message || fallbackMessage;
        }

        const text = (await response.text()).trim();
        return text || fallbackMessage;
    } catch (_) {
        return fallbackMessage;
    }
}

async function startLivenessSessionWithRetry(transactionId) {
    let lastError = null;

    for (let attempt = 1; attempt <= LIVENESS_START_MAX_ATTEMPTS; attempt++) {
        const isRetry = attempt > 1;
        if (isRetry) {
            setLivenessState('warning', `Reconnecting to server... attempt ${attempt}/${LIVENESS_START_MAX_ATTEMPTS}`);
            showLivenessAlert('Unstable server connection. Trying again...', 'warning');
            await sleep(650 * attempt);
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), LIVENESS_START_TIMEOUT_MS);

        try {
            const response = await fetch('/api/liveness-stream/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    transaction_id: transactionId,
                    risk_level: 'medium'
                }),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const fallbackMessage = `Error ${response.status} starting session`;
                const detail = await readResponseError(response, fallbackMessage);

                if (LIVENESS_START_RETRYABLE_STATUS.has(response.status) && attempt < LIVENESS_START_MAX_ATTEMPTS) {
                    lastError = new Error(detail);
                    continue;
                }

                throw new Error(detail);
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            const isAbort = error?.name === 'AbortError';
            const retryableNetworkError = isAbort || error instanceof TypeError;

            if (retryableNetworkError && attempt < LIVENESS_START_MAX_ATTEMPTS) {
                lastError = new Error(isAbort ? 'Server timeout while starting liveness session' : error.message);
                continue;
            }

            throw error;
        }
    }

    throw lastError || new Error('Failed to start liveness session');
}

async function runFaceCompareInsideLiveness(userId) {
    const statusResponse = await fetch(`/api/face-id/status/${userId}`);
    const statusData = await statusResponse.json();

    if (!statusResponse.ok || !statusData.available) {
        throw new Error(statusData.detail || 'Face identity service unavailable');
    }

    if (!statusData.enrolled) {
        throw new Error('No master selfie found. Please enroll first.');
    }

    const storedPreview = document.getElementById('stored-selfie-preview');
    if (storedPreview) {
        storedPreview.src = statusData.reference_image_base64 || '';
    }

    let frameBase64 = null;
    for (let i = 0; i < 10; i++) {
        frameBase64 = captureFrame();
        if (frameBase64) break;
        await new Promise((resolve) => setTimeout(resolve, 120));
    }

    if (!frameBase64) {
        throw new Error('Could not capture webcam frame for face comparison');
    }

    const verifyResponse = await fetch('/api/face-id/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            image_base64: frameBase64,
            consent_to_store: false,
        })
    });

    const verifyData = await verifyResponse.json();
    if (!verifyResponse.ok) {
        throw new Error(verifyData.detail || 'Face comparison failed');
    }

    if (!verifyData.match) {
        throw new Error(`Face mismatch (${verifyData.confidence?.toFixed?.(1) ?? verifyData.confidence}% confidence)`);
    }

    return verifyData;
}

async function forceFailLivenessSession(sessionId, reason) {
    const response = await fetch(`/api/liveness-stream/fail/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason })
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.detail || `Error ${response.status} force-failing liveness session`);
    }
    return data;
}

/* ==============================================
   WEBCAM INIT / STOP
   ============================================== */

async function initWebcam() {
    try {
        console.log('[Webcam] Requesting access...');

        const constraints = {
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user',
                frameRate: { ideal: 30 }
            },
            audio: false
        };

        webcamStream = await navigator.mediaDevices.getUserMedia(constraints);

        webcamVideo = document.getElementById('webcam');
        if (!webcamVideo) {
            throw new Error('Element #webcam not found in DOM');
        }

        webcamVideo.srcObject = webcamStream;

        // Mirror display only — backend receives raw (un-flipped) frames.
        // The detector does NOT flip internally for the web flow.
        webcamVideo.style.transform = 'scaleX(-1)';
        webcamVideo.style.webkitTransform = 'scaleX(-1)';

        // Wait until video is actually playing before we start capturing
        await new Promise((resolve, reject) => {
            webcamVideo.onloadedmetadata = () => {
                webcamVideo.play().then(resolve).catch(reject);
            };
            webcamVideo.onerror = reject;
        });

        console.log('[Webcam] Started successfully');
        return webcamStream;

    } catch (error) {
        console.error('[Webcam] Error:', error);

        let errorMessage = 'Unable to access the camera.';
        if (error.name === 'NotAllowedError') {
            errorMessage = 'Permission denied. Please allow camera access in browser settings.';
        } else if (error.name === 'NotFoundError') {
            errorMessage = 'No camera found on this device.';
        } else if (error.name === 'NotReadableError') {
            errorMessage = 'The camera is in use by another application. Close it and try again.';
        } else if (error.message.includes('#webcam')) {
            errorMessage = 'Internal error: video element not found. Refresh the page.';
        }

        if (typeof showError === 'function') showError(errorMessage);
        throw error;
    }
}

function stopWebcam() {
    if (captureInterval) {
        clearInterval(captureInterval);
        captureInterval = null;
    }

    isCapturing = false;

    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }

    if (webcamVideo) {
        webcamVideo.srcObject = null;
        webcamVideo = null;
    }

    console.log('[Webcam] Stopped');
}

/* ==============================================
   FRAME CAPTURE
   ============================================== */

function captureFrame() {
    if (!webcamVideo || !webcamVideo.videoWidth || !webcamVideo.videoHeight) {
        return null;
    }

    const canvas = document.createElement('canvas');
    canvas.width = webcamVideo.videoWidth;
    canvas.height = webcamVideo.videoHeight;

    const ctx = canvas.getContext('2d');

    // Draw WITHOUT flipping — the CSS mirror is for display only.
    // The backend (MediaPipe) expects the raw orientation.
    ctx.drawImage(webcamVideo, 0, 0, canvas.width, canvas.height);

    // JPEG at 75% — good balance between quality and payload size at 12fps
    return canvas.toDataURL('image/jpeg', 0.75);
}

/* ==============================================
   LIVENESS VERIFICATION FLOW
   ============================================== */

async function startLivenessVerification(transactionId, userId) {
    if (isStartingLiveness || isCapturing) {
        console.warn('[Liveness] Start ignored: session already starting/running');
        return;
    }

    isStartingLiveness = true;
    currentTransactionId = transactionId;
    updateRppgTelemetry({
        rppg_bpm: null,
    });

    try {
        console.log('[Liveness] Starting session for transaction:', transactionId);
        showLivenessModal();
        setLivenessState('normal', 'Validating presence...');
        hideLivenessAlert();

        await initWebcam();

        updateChallengeUI('Identity check in progress', 'Comparing live webcam with your stored master selfie...');
        updateProgress(5);
        setLivenessState('normal', 'Confirming identity...');

        await runFaceCompareInsideLiveness(userId);

        updateChallengeUI('Identity confirmed', 'Face match successful. Starting liveness challenges...');
        updateProgress(12);
        setLivenessState('normal', 'Identity confirmed');

        const data = await startLivenessSessionWithRetry(transactionId);
        const sessionId = data.session_id;
        activeSessionId = sessionId;
        activeRunId += 1;

        console.log('[Liveness] Session started:', sessionId);
        console.log('[Liveness] Challenges:', data.total_challenges);

        // Show first challenge immediately
        updateChallengeUI(
            data.current_challenge.instruction || data.current_challenge.name,
            'Keep your face centered in the camera...'
        );
        updateProgress(0);
        setLivenessState('normal', 'Challenges started');
        hideLivenessAlert();

        startFrameStream(sessionId, activeRunId, userId);

    } catch (error) {
        console.error('[Liveness] Startup error:', error);
        setLivenessState('error', 'Could not start');
        showLivenessAlert('Failed to start liveness challenges. Check your connection and try again.', 'error');
        if (typeof showError === 'function') {
            showError('Error starting biometric verification: ' + error.message);
        } else {
            alert('Error starting biometric verification: ' + error.message);
        }
        stopWebcam();
        hideLivenessModal();
    } finally {
        isStartingLiveness = false;
    }
}

function startFrameStream(sessionId, runId, userId) {
    if (captureInterval) {
        clearInterval(captureInterval);
        captureInterval = null;
    }

    isCapturing = true;
    let framesSent = 0;
    let lastIdentityCheckAt = 0;
    let identityCheckInFlight = false;
    let identityMismatchCount = 0;
    let identityFailureTriggered = false;

    // 12 FPS — reliable for blink detection even with cloud round-trip latency.
    // A blink (~150ms) = ~1.8 frames at this rate, giving enough coverage.
    const FPS = 12;
    const INTERVAL_MS = 1000 / FPS;

    // In-flight guard: skip tick if previous request hasn't returned yet.
    // Prevents frame pile-up when the Render server is under load.
    let requestInFlight = false;

    console.log(`[Liveness] Frame stream starting at ${FPS}fps`);

    captureInterval = setInterval(async () => {
        // Drop stale streams from previous sessions/runs.
        if (runId !== activeRunId || sessionId !== activeSessionId) {
            clearInterval(captureInterval);
            return;
        }

        if (!isCapturing) {
            clearInterval(captureInterval);
            return;
        }

        // Skip this tick if the last request is still pending
        if (requestInFlight) {
            return;
        }

        const frameBase64 = captureFrame();
        if (!frameBase64) {
            // Video not ready yet — skip silently
            return;
        }

        // Continuous identity guard: periodically compare live frame with stored selfie
        // during the full liveness flow to detect person swaps.
        if (
            userId
            && !identityFailureTriggered
            && !identityCheckInFlight
            && (Date.now() - lastIdentityCheckAt) >= IDENTITY_CHECK_INTERVAL_MS
        ) {
            lastIdentityCheckAt = Date.now();
            identityCheckInFlight = true;

            fetch('/api/face-id/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    image_base64: frameBase64,
                    consent_to_store: false,
                })
            })
                .then(async (resp) => {
                    const data = await resp.json().catch(() => ({}));
                    if (!resp.ok) {
                        console.warn('[Identity Guard] verify error:', data.detail || resp.status);
                        return;
                    }

                    if (data.match) {
                        identityMismatchCount = 0;
                        return;
                    }

                    identityMismatchCount += 1;
                    console.warn(`[Identity Guard] mismatch ${identityMismatchCount}/${MAX_IDENTITY_MISMATCHES}`);

                    if (identityMismatchCount < MAX_IDENTITY_MISMATCHES || identityFailureTriggered) {
                        return;
                    }

                    identityFailureTriggered = true;
                    clearInterval(captureInterval);
                    isCapturing = false;
                    setLivenessState('error', 'Identity error');
                    showLivenessAlert('Different person detected during verification. Transaction rejected.', 'error');
                    updateChallengeUI('Identity mismatch detected', 'Different person detected. Rejecting transaction...');

                    try {
                        const failResult = await forceFailLivenessSession(
                            sessionId,
                            'Identity changed during liveness. Transaction rejected.'
                        );

                        activeSessionId = null;
                        stopWebcam();
                        hideLivenessModal();

                        if (typeof window.onLivenessCompleted === 'function') {
                            window.onLivenessCompleted(failResult);
                        }
                    } catch (failError) {
                        console.error('[Identity Guard] force-fail error:', failError);
                        stopWebcam();
                        hideLivenessModal();
                        if (typeof showError === 'function') {
                            showError('Identity changed during liveness. Transaction rejected.');
                        }
                    }
                })
                .catch((err) => {
                    console.warn('[Identity Guard] request error:', err.message);
                })
                .finally(() => {
                    identityCheckInFlight = false;
                });
        }

        requestInFlight = true;

        try {
            const response = await fetch(`/api/liveness-stream/frame/${sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame_base64: frameBase64 })
            });

            if (!response.ok) {
                if (response.status === 429) {
                    console.warn('[Liveness] Rate limit hit — pausing 2s');
                    await new Promise(r => setTimeout(r, 2000));
                    return;
                }
                if (response.status === 404) {
                    console.error('[Liveness] Session expired');
                    clearInterval(captureInterval);
                    isCapturing = false;
                    if (typeof showError === 'function') {
                        showError('Session expired. Start the transaction again.');
                    }
                    stopWebcam();
                    hideLivenessModal();
                    return;
                }
                if (response.status === 400) {
                    // Bad frame decode — skip this frame only
                    return;
                }
                console.warn('[Liveness] Unexpected status:', response.status);
                return;
            }

            const result = await response.json();

            if (identityFailureTriggered) {
                return;
            }

            // Ignore late responses from stale runs/sessions.
            if (runId !== activeRunId || sessionId !== activeSessionId) {
                return;
            }

            framesSent++;

            // Update UI — prefer instruction over name for clearer UX
            const instruction = result.current_challenge?.instruction
                || result.current_challenge?.name
                || '';
            updateChallengeUI(instruction, result.feedback);
            updateProgress(result.progress);
            updateRppgTelemetry(result);

            const feedback = (result.feedback || '').toLowerCase();
            if (result.status === 'failed') {
                setLivenessState('error', 'Verification failed');
            } else if (feedback.includes('face not detected')) {
                setLivenessState('warning', 'Face not detected');
            } else {
                setLivenessState('normal', 'Verification in progress');
            }

            if (feedback.includes('face lost for more than')) {
                showLivenessAlert(
                    `Face missing for over ${NO_FACE_CANCEL_SECONDS}s. Transaction cancelled for security.`,
                    'error'
                );
            } else if (feedback.includes('face not detected')) {
                showLivenessAlert('Stay in front of the camera to continue.', 'warning');
            } else {
                hideLivenessAlert();
            }

            if (framesSent % 16 === 0) {
                console.log(
                    `[Liveness] Frame ${framesSent} | ${result.progress.toFixed(1)}% | ${result.feedback} | ` +
                    `rPPG: bpm=${result.rppg_bpm ?? 'None'} raw=${result.rppg_raw_bpm ?? 'None'} ready=${result.rppg_signal_ready} reason=${result.rppg_debug_reason ?? 'n/a'}`
                );
            }

            if (result.status === 'completed') {
                console.log('[Liveness] COMPLETED');
                clearInterval(captureInterval);
                isCapturing = false;
                setLivenessState('normal', 'Verification completed');
                await completeLivenessVerification(sessionId, true);
            } else if (result.status === 'failed') {
                console.log('[Liveness] FAILED:', result.feedback);
                clearInterval(captureInterval);
                isCapturing = false;

                if (feedback.includes('face lost for more than')) {
                    updateChallengeUI('Face absence detected', `No face for over ${NO_FACE_CANCEL_SECONDS}s. Terminating...`);
                    await new Promise((resolve) => setTimeout(resolve, 900));
                }

                await completeLivenessVerification(sessionId, false);
            }

        } catch (error) {
            // Network errors are transient — log but keep streaming
            console.warn('[Liveness] Frame send error (will retry):', error.message);
        } finally {
            requestInFlight = false;
        }

    }, INTERVAL_MS);
}

async function completeLivenessVerification(sessionId, success) {
    console.log(`[Liveness] Completing session — success: ${success}`);

    try {
        const response = await fetch(`/api/liveness-stream/complete/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            let detail = `HTTP ${response.status}`;
            try {
                const err = await response.json();
                detail = err.detail || detail;
            } catch (_) {}
            throw new Error(`Failed to complete verification: ${detail}`);
        }

        const result = await response.json();
        console.log('[Liveness] Final result:', result);
        
        activeSessionId = null;
        stopWebcam();
        hideLivenessModal();

        if (typeof window.onLivenessCompleted === 'function') {
            window.onLivenessCompleted(result);
        } else if (result.transaction) {
            if (typeof window.showTransactionResult === 'function') {
                window.showTransactionResult(result.transaction, success);
            } else {
                alert(success ? '✅ Verification approved!' : '❌ Verification failed.');
            }
        }

    } catch (error) {
        console.error('[Liveness] Complete error:', error);
        if (typeof showError === 'function') {
            showError('Error completing verification: ' + error.message);
        } else {
            alert('Error completing verification: ' + error.message);
        }
        stopWebcam();
        hideLivenessModal();
    }
}

function cancelLiveness() {
    console.log('[Liveness] Cancelled by user');
    isCapturing = false;
    activeRunId += 1;

    const sessionToCancel = activeSessionId;
    activeSessionId = null;

    if (sessionToCancel) {
        fetch(`/api/liveness-stream/cancel/${sessionToCancel}`, { method: 'DELETE' })
            .catch((error) => console.warn('[Liveness] Cancel session request failed:', error.message));
    }

    updateRppgTelemetry({
        rppg_bpm: null,
    });
    stopWebcam();
    hideLivenessModal();
    if (typeof showInfo === 'function') {
        showInfo('Verification canceled. The transaction will remain pending.');
    }
}

/* ==============================================
   UI HELPERS
   ============================================== */

function showLivenessModal() {
    const modal = document.getElementById('liveness-modal');
    if (modal) modal.classList.remove('hidden');

    const debugPanel = document.getElementById('rppg-debug-panel');
    const debugOverlay = document.getElementById('webcam-debug-overlay');
    if (RPPG_DEBUG_MODE) {
        debugPanel?.classList.remove('hidden');
        debugOverlay?.classList.remove('hidden');
    } else {
        debugPanel?.classList.add('hidden');
        debugOverlay?.classList.add('hidden');
    }

    hideLivenessAlert();
    setLivenessState('normal', 'Preparing verification...');
}

function hideLivenessModal() {
    const modal = document.getElementById('liveness-modal');
    if (modal) modal.classList.add('hidden');

    const debugOverlay = document.getElementById('webcam-debug-overlay');
    if (debugOverlay) {
        const ctx = debugOverlay.getContext('2d');
        if (ctx) {
            ctx.clearRect(0, 0, debugOverlay.width, debugOverlay.height);
        }
    }

    hideLivenessAlert();
}

function drawRppgDebugOverlay(result) {
    if (!RPPG_DEBUG_MODE) return;

    const overlay = document.getElementById('webcam-debug-overlay');
    const video = document.getElementById('webcam');
    const rois = result?.rppg_debug_visual?.rois;
    if (!overlay || !video) return;

    const width = video.clientWidth || overlay.clientWidth;
    const height = video.clientHeight || overlay.clientHeight;
    if (!width || !height) return;

    if (overlay.width !== width) overlay.width = width;
    if (overlay.height !== height) overlay.height = height;

    const ctx = overlay.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, overlay.width, overlay.height);

    if (!rois) return;

    const drawPolygon = (points, stroke, fill) => {
        if (!Array.isArray(points) || points.length < 3) return;
        ctx.beginPath();
        ctx.moveTo(points[0][0] * overlay.width, points[0][1] * overlay.height);
        for (let i = 1; i < points.length; i++) {
            ctx.lineTo(points[i][0] * overlay.width, points[i][1] * overlay.height);
        }
        ctx.closePath();
        ctx.fillStyle = fill;
        ctx.strokeStyle = stroke;
        ctx.lineWidth = 2;
        ctx.fill();
        ctx.stroke();
    };

    drawPolygon(rois.forehead, 'rgba(34,211,238,0.95)', 'rgba(34,211,238,0.18)');
    drawPolygon(rois.left_cheek, 'rgba(132,204,22,0.95)', 'rgba(132,204,22,0.18)');
    drawPolygon(rois.right_cheek, 'rgba(251,146,60,0.95)', 'rgba(251,146,60,0.18)');
}

function updateRppgDebugPanel(result) {
    if (!RPPG_DEBUG_MODE) return;

    const qualityEl = document.getElementById('rppg-debug-quality');
    const snrEl = document.getElementById('rppg-debug-snr');
    const peakEl = document.getElementById('rppg-debug-peak');
    const pulseEl = document.getElementById('rppg-debug-pulse');
    const reasonEl = document.getElementById('rppg-debug-reason');
    if (!qualityEl || !snrEl || !peakEl || !pulseEl || !reasonEl) return;

    const quality = Number(result?.rppg_quality_score ?? 0);
    const metrics = result?.rppg_quality_metrics ?? {};
    const qualityPct = Math.round(Math.max(0, Math.min(1, quality)) * 100);

    qualityEl.textContent = `Quality: ${qualityPct}%`;
    qualityEl.className = `font-semibold ${qualityPct >= 70 ? 'text-emerald-300' : qualityPct >= 50 ? 'text-amber-300' : 'text-red-300'}`;
    snrEl.textContent = Number.isFinite(metrics.snr) ? metrics.snr.toFixed(2) : '--';
    peakEl.textContent = Number.isFinite(metrics.peak_power_ratio) ? metrics.peak_power_ratio.toFixed(3) : '--';
    pulseEl.textContent = Number.isFinite(metrics.pulse_rms_ratio) ? metrics.pulse_rms_ratio.toFixed(3) : '--';
    reasonEl.textContent = result?.rppg_debug_reason || '--';
}

function setLivenessState(state, text) {
    const dotEl = document.getElementById('liveness-state-dot');
    const textEl = document.getElementById('liveness-state-text');

    if (dotEl) {
        dotEl.classList.remove('liveness-state-normal', 'liveness-state-warning', 'liveness-state-error');
        if (state === 'warning') {
            dotEl.classList.add('liveness-state-warning');
        } else if (state === 'error') {
            dotEl.classList.add('liveness-state-error');
        } else {
            dotEl.classList.add('liveness-state-normal');
        }
    }

    if (textEl && text) {
        textEl.textContent = text;
    }
}

function showLivenessAlert(message, type = 'warning') {
    const alertEl = document.getElementById('liveness-alert');
    const textEl = document.getElementById('liveness-alert-text');

    if (!alertEl || !textEl || !message) {
        return;
    }

    alertEl.classList.remove('hidden', 'bg-amber-50', 'border-amber-200', 'text-amber-900', 'bg-red-50', 'border-red-200', 'text-red-900');
    if (type === 'error') {
        alertEl.classList.add('bg-red-50', 'border-red-200', 'text-red-900');
    } else {
        alertEl.classList.add('bg-amber-50', 'border-amber-200', 'text-amber-900');
    }

    textEl.textContent = message;
}

function hideLivenessAlert() {
    const alertEl = document.getElementById('liveness-alert');
    if (alertEl) {
        alertEl.classList.add('hidden');
    }
}

function updateRppgTelemetry(result) {
    const bpmEl = document.getElementById('rppg-bpm');

    if (!bpmEl) {
        return;
    }

    const bpm = result?.rppg_bpm;

    bpmEl.textContent = Number.isFinite(bpm) ? bpm.toFixed(1) : 'Measuring...';

    updateRppgDebugPanel(result);
    drawRppgDebugOverlay(result);
}

function updateChallengeUI(instruction, feedback) {
    const instructionEl = document.getElementById('challenge-instruction');
    const statusEl = document.getElementById('challenge-status');
    if (instructionEl && instruction) instructionEl.textContent = instruction;
    if (statusEl && feedback) statusEl.textContent = feedback;
}

function updateProgress(progress) {
    const progressBar = document.getElementById('liveness-progress');
    if (progressBar) {
        progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
    }
}

console.log('[BioTrust] Webcam module v2.4 loaded');