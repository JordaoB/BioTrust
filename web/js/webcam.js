/* ==============================================
   BioTrust - Webcam & Liveness Handler v2.2
   ==============================================

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

async function startLivenessVerification(transactionId) {
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

        await initWebcam();

        const response = await fetch('/api/liveness-stream/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                transaction_id: transactionId,
                risk_level: 'medium'
            })
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Error ${response.status} starting session`);
        }

        const data = await response.json();
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

        startFrameStream(sessionId, activeRunId);

    } catch (error) {
        console.error('[Liveness] Startup error:', error);
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

function startFrameStream(sessionId, runId) {
    if (captureInterval) {
        clearInterval(captureInterval);
        captureInterval = null;
    }

    isCapturing = true;
    let framesSent = 0;

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
                await completeLivenessVerification(sessionId, true);
            } else if (result.status === 'failed') {
                console.log('[Liveness] FAILED:', result.feedback);
                clearInterval(captureInterval);
                isCapturing = false;
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
}

function hideLivenessModal() {
    const modal = document.getElementById('liveness-modal');
    if (modal) modal.classList.add('hidden');
}

function updateRppgTelemetry(result) {
    const bpmEl = document.getElementById('rppg-bpm');

    if (!bpmEl) {
        return;
    }

    const bpm = result?.rppg_bpm;

    bpmEl.textContent = Number.isFinite(bpm) ? bpm.toFixed(1) : 'A medir...';
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

console.log('[BioTrust] Webcam module v2.2 loaded');