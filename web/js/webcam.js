/* ==============================================
   BioTrust - Webcam & Liveness Handler
   ==============================================
   
   Este módulo gere a captura de vídeo da webcam e
   a comunicação com o backend para verificação de liveness.
   
   FLUXO:
   1. Solicitar permissão da câmara (getUserMedia)
   2. Exibir stream de vídeo no elemento <video>
   3. Capturar frames periodicamente
   4. Enviar frames para o backend via WebSocket ou HTTP
   5. Receber instruções (desafios) e feedback
   6. Mostrar resultado final
   
   TECNOLOGIAS:
   - MediaDevices API (getUserMedia)
   - Canvas API (para capturar frames)
   - WebSocket (opcional - real-time)
   - HTTP POST (alternativa mais simples)
   
   ============================================== */

// Estado global da webcam
let webcamStream = null;
let webcamVideo = null;
let isCapturing = false;
let captureInterval = null;
let currentTransactionId = null;
let challengesCompleted = 0;
let totalChallenges = 0;

/* ==============================================
   INICIALIZAÇÃO DA WEBCAM
   ============================================== */

/**
 * Solicita permissão e inicia a webcam
 * @returns {Promise<MediaStream>} - Stream de vídeo
 */
async function initWebcam() {
    try {
        console.log('📹 Solicitando acesso à webcam...');
        
        // Solicita permissão ao utilizador
        // Constraints: preferências de vídeo
        const constraints = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user', // Câmara frontal
                frameRate: { ideal: 30 }
            },
            audio: false // Não precisamos de áudio
        };
        
        webcamStream = await navigator.mediaDevices.getUserMedia(constraints);
        
        // Conecta o stream ao elemento <video>
        webcamVideo = document.getElementById('webcam');
        webcamVideo.srcObject = webcamStream;
        // Keep preview non-mirrored so left/right instructions match user movement.
        webcamVideo.style.transform = 'none';
        webcamVideo.style.webkitTransform = 'none';
        
        console.log('✅ Webcam iniciada com sucesso');
        return webcamStream;
        
    } catch (error) {
        console.error('❌ Erro ao aceder à webcam:', error);
        
        // Mensagens de erro amigáveis
        let errorMessage = 'Não foi possível aceder à câmara.';
        
        if (error.name === 'NotAllowedError') {
            errorMessage = 'Permissão negada. Por favor, autorize o acesso à câmara.';
        } else if (error.name === 'NotFoundError') {
            errorMessage = 'Nenhuma câmara encontrada no dispositivo.';
        } else if (error.name === 'NotReadableError') {
            errorMessage = 'A câmara está a ser usada por outra aplicação.';
        }
        
        showError(errorMessage);
        throw error;
    }
}

/**
 * Para a webcam e liberta recursos
 */
function stopWebcam() {
    if (webcamStream) {
        console.log('🛑 Parando webcam...');
        
        // Para todas as tracks (vídeo/áudio)
        webcamStream.getTracks().forEach(track => track.stop());
        
        // Limpa o elemento de vídeo
        if (webcamVideo) {
            webcamVideo.srcObject = null;
        }
        
        webcamStream = null;
        isCapturing = false;
        
        // Limpa o intervalo de captura
        if (captureInterval) {
            clearInterval(captureInterval);
            captureInterval = null;
        }
        
        console.log('✅ Webcam parada');
    }
}

/* ==============================================
   CAPTURA DE FRAMES
   ============================================== */

/**
 * Captura um frame do vídeo como imagem Base64
 * @returns {string} - Imagem em formato Base64
 */
function captureFrame() {
    if (!webcamVideo) {
        console.warn('⚠️ Vídeo não inicializado');
        return null;
    }
    
    // Cria um canvas temporário para capturar o frame
    const canvas = document.createElement('canvas');
    canvas.width = webcamVideo.videoWidth;
    canvas.height = webcamVideo.videoHeight;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(webcamVideo, 0, 0, canvas.width, canvas.height);
    
    // Converte para Base64 (JPEG com 80% de qualidade)
    const frameBase64 = canvas.toDataURL('image/jpeg', 0.8);
    
    return frameBase64;
}

/**
 * Envia um frame para o backend para análise
 * @param {string} frameBase64 - Imagem em Base64
 * @returns {Promise<object>} - Resposta do backend
 */
async function sendFrameToBackend(frameBase64) {
    // NOTA: O backend atual não tem endpoint para processar frames em tempo real
    // Vamos simular por enquanto e depois implementar
    
    // TODO: Implementar endpoint /api/liveness/analyze-frame
    // Por agora, vamos usar a simulação
    
    console.log('📤 Frame capturado (simulado)');
    return { success: true };
}

/* ==============================================
   LIVENESS VERIFICATION FLOW
   ============================================== */

/**
 * Inicia o processo de verificação de liveness
 * @param {string} transactionId - ID da transação a verificar
 */
/**
 * Inicia verificação de liveness
 * Agora usa LivenessDetectorV3 real via API
 */
async function startLivenessVerification(transactionId) {
    currentTransactionId = transactionId;
    challengesCompleted = 0;
    
    try {
        console.log('🔍 Iniciando verificação de liveness com detector V3...');
        showLivenessModal();
        
        // 1. Iniciar webcam primeiro
        await initWebcam();
        
        // 2. Iniciar sessão de liveness no backend
        const response = await fetch('/api/liveness-stream/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                transaction_id: transactionId,
                risk_level: 'medium'
            })
        });
        
        if (!response.ok) {
            throw new Error('Falha ao iniciar sessão de liveness');
        }
        
        const data = await response.json();
        const sessionId = data.session_id;
        
        console.log('✅ Sessão iniciada:', sessionId);
        console.log('📋 Desafios:', data.total_challenges);
        console.log('🎯 Primeiro desafio:', data.current_challenge.name);
        
        // 3. Iniciar loop de captura e processamento
        startFrameStream(sessionId);
        
    } catch (error) {
        console.error('❌ Erro ao iniciar liveness:', error);
        alert('Erro ao iniciar verificação biométrica: ' + error.message);
        stopWebcam();
        hideLivenessModal();
    }
}

/**
 * Inicia stream de frames para o backend (REAL LIVENESS DETECTOR V3)
 * @param {string} sessionId - ID da sessão de liveness
 */
function startFrameStream(sessionId) {
    isCapturing = true;
    let framesSent = 0;
    const FPS = 10; // 10 frames por segundo (reduz carga)
    const INTERVAL_MS = 1000 / FPS;
    
    console.log(`🎥 Iniciando stream de frames (${FPS} fps)`);
    
    captureInterval = setInterval(async () => {
        if (!isCapturing || !webcamVideo) {
            console.log('⏸️ Stream pausado ou webcam não disponível');
            clearInterval(captureInterval);
            return;
        }
        
        try {
            // Capturar frame atual
            const frameBase64 = captureFrame();
            
            if (!frameBase64) {
                console.warn('⚠️ Frame vazio, pulando...');
                return;
            }
            
            // Enviar frame para backend
            const response = await fetch(`/api/liveness-stream/frame/${sessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame_base64: frameBase64 })
            });
            
            if (!response.ok) {
                console.error('❌ Erro ao processar frame:', response.statusText);
                return;
            }
            
            const result = await response.json();
            framesSent++;
            
            // Atualizar UI com feedback do backend
            updateChallengeUI(result.current_challenge.instruction, result.feedback);
            updateProgress(result.progress);
            
            console.log(`📊 Frame ${framesSent}: ${result.progress.toFixed(1)}% - ${result.feedback}`);
            
            // Verificar se completou
            if (result.status === 'completed') {
                console.log('✅ Verificação COMPLETA!');
                clearInterval(captureInterval);
                await completeLivenessVerification(sessionId, true);
            } else if (result.status === 'failed' || result.status === 'timeout') {
                console.log('❌ Verificação FALHOU:', result.status);
                clearInterval(captureInterval);
                await completeLivenessVerification(sessionId, false);
            }
            
        } catch (error) {
            console.error('❌ Erro ao enviar frame:', error);
            // Não para o stream por erros individuais, continua tentando
        }
        
    }, INTERVAL_MS);
}

/**
 * Completa a verificação de liveness (COM API REAL)
 * @param {string} sessionId - ID da sessão
 * @param {boolean} success - Se passou ou não
 */
async function completeLivenessVerification(sessionId, success) {
    console.log(`🎯 Finalizando verificação... ${success ? 'SUCESSO' : 'FALHA'}`);
    
    isCapturing = false;
    
    try {
        // Chamar endpoint de finalização
        const response = await fetch(`/api/liveness-stream/complete/${sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            throw new Error('Falha ao finalizar verificação');
        }
        
        const result = await response.json();
        
        console.log('✅ Resultado final:', result);
        
        // Parar webcam
        stopWebcam();
        
        // Fechar modal
        hideLivenessModal();
        
        // Callback opcional para páginas que integram este módulo
        if (typeof window.onLivenessCompleted === 'function') {
            window.onLivenessCompleted(result);
        } else if (result.transaction) {
            if (typeof window.showTransactionResult === 'function') {
                window.showTransactionResult(result.transaction, true);
            } else {
                alert(success ? '✅ Verificação aprovada!' : '❌ Verificação falhou.');
            }
        }
        
    } catch (error) {
        console.error('❌ Erro ao completar liveness:', error);
        alert('Erro ao finalizar verificação: ' + error.message);
        stopWebcam();
        hideLivenessModal();
    }
}

/**
 * Cancela a verificação de liveness
 */
function cancelLiveness() {
    console.log('❌ Verificação cancelada pelo utilizador');
    
    stopWebcam();
    hideLivenessModal();
    
    // Volta para o resultado da transação
    showInfo('Verificação cancelada. A transação ficará pendente até completar a verificação.');
}

/* ==============================================
   UI HELPERS
   ============================================== */

/**
 * Mostra o modal de liveness
 */
function showLivenessModal() {
    const modal = document.getElementById('liveness-modal');
    modal.classList.remove('hidden');
}

/**
 * Esconde o modal de liveness
 */
function hideLivenessModal() {
    const modal = document.getElementById('liveness-modal');
    modal.classList.add('hidden');
}

/**
 * Atualiza a UI com o desafio atual
 * @param {string} instruction - Instrução do desafio
 * @param {string} status - Status atual
 */
function updateChallengeUI(instruction, status) {
    const instructionEl = document.getElementById('challenge-instruction');
    const statusEl = document.getElementById('challenge-status');
    
    if (instructionEl) instructionEl.textContent = instruction;
    if (statusEl) statusEl.textContent = status;
}

/**
 * Atualiza a barra de progresso
 * @param {number} progress - Progresso em % (0-100)
 */
function updateProgress(progress) {
    const progressBar = document.getElementById('liveness-progress');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
}

/* ==============================================
   EXPORT & INITIALIZATION
   ============================================== */

console.log('✅ Webcam Module Loaded');
console.log('📹 Available functions:', [
    'initWebcam()',
    'stopWebcam()',
    'captureFrame()',
    'startLivenessVerification(transactionId)',
    'cancelLiveness()'
]);
