# 🔐 BioTrust

> **"Deepfakes não têm pulsação"**  
> Sistema inteligente de autenticação biométrica com deteção de liveness para pagamentos seguros.

[![TecStorm '26](https://img.shields.io/badge/TecStorm-'26-blue)](https://tecstorm.pt)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.13-red.svg)](https://opencv.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.9-orange.svg)](https://mediapipe.dev/)

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [O Problema](#-o-problema)
- [A Nossa Solução](#-a-nossa-solução)
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Estado Atual do Projeto](#-estado-atual-do-projeto)
- [Stack Tecnológica](#-stack-tecnológica)
- [Instalação e Execução](#-instalação-e-execução)
- [Como Funciona](#-como-funciona)
- [Roadmap](#-roadmap)
- [Equipa](#-equipa)

---

## 🎯 Visão Geral

**BioTrust** é uma camada de segurança inteligente (Trust Layer) para gateways de pagamento que combina:
- 🧠 **Motor de Risco Contextual** - Análise inteligente de transações
- 💓 **Liveness Detection** - Prova de vida por webcam (sem hardware adicional)
- 🔒 **Integração Simples** - API REST para qualquer sistema de pagamento

Este projeto foi desenvolvido durante o **Hackathon TecStorm '26** na categoria **Payments Without Limits**.

---

## ❌ O Problema

Com o avanço da Inteligência Artificial, os **Deepfakes** tornaram-se uma ameaça real:

- ✔️ Reconhecimento facial tradicional → ❌ Facilmente enganado por vídeos ou fotos
- ✔️ Autenticação por selfie → ❌ Vulnerável a ataques de apresentação
- ✔️ Pagamentos biométricos → ❌ Sem validação de vida real

**Resultado:** Fraudes em pagamentos digitais custam milhões anualmente.

---

## ✅ A Nossa Solução

### **Arquitetura em 2 Camadas**

#### **1️⃣ Motor de Risco Contextual**
Analisa automaticamente cada transação:
- 📍 **Localização** - GPS e padrões de movimento
- 💰 **Valor** - Montante comparado com histórico
- 🕒 **Contexto** - Horário, tipo de compra, dispositivo

**Decisão Inteligente:**
- **Baixo Risco** → Aprovação imediata ⚡
- **Alto Risco** → Aciona Liveness Detection 🔍

#### **2️⃣ Liveness Detection (Prova de Vida)**

##### **Active Liveness** ✅ *[IMPLEMENTADO]*
Pede ao utilizador ações em tempo real:
- 👁️ Piscar os olhos 3 vezes
- ↩️ Virar a cabeça para esquerda e voltar
- ↪️ Virar a cabeça para direita e voltar

##### **Passive Liveness (rPPG)** 🚧 *[EM DESENVOLVIMENTO]*
Deteta batimento cardíaco através da webcam:
- Analisa micro-mudanças de cor na pele
- Funciona com câmara comum (sem sensores)
- Invisível para o utilizador (não requer ações)

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                       FRONTEND WEB                          │
│  (Simulação de Interface Bancária + Dashboard de Testes)   │
└────────────────────┬────────────────────────────────────────┘
                     │ API REST
┌────────────────────▼────────────────────────────────────────┐
│                  BACKEND (Python)                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Motor de Risco Contextual                    │  │
│  │  • Análise de localização                            │  │
│  │  • Avaliação de valor                                │  │
│  │  • Score de risco                                    │  │
│  └───────────────────┬──────────────────────────────────┘  │
│                      │                                      │
│                      ▼ (se risco > threshold)              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Liveness Detection Module                    │  │
│  │  • Active Liveness (OpenCV + MediaPipe)             │  │
│  │  • Passive Liveness rPPG (futuro)                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Estado Atual do Projeto

### ✅ **Concluído**

- [x] Ideação e validação do problema
- [x] Análise SWOT completa
- [x] Matriz de seleção de problema (Urgência/Severidade/Impacto)
- [x] Relatório DevPost estruturado
- [x] **Active Liveness Detection funcionando** 🎉
  - Deteção de piscadelas (Eye Aspect Ratio)
  - Deteção de rotação da cabeça (Yaw/Pitch)
  - Sistema sequencial de 3 fases
  - Interface visual com instruções

### 🚧 **Em Desenvolvimento**

- [ ] Motor de Risco Contextual (backend Python)
- [ ] API REST (FastAPI ou Flask)
- [ ] Frontend Web (React ou HTML/JS)
- [ ] Dashboard de simulação de cenários
- [ ] Passive Liveness (rPPG)

### 📝 **Backlog / Futuro**

- [ ] Integração com sistemas de pagamento reais
- [ ] Anti-spoofing avançado (deteção de máscaras)
- [ ] Testes de segurança e penetration testing
- [ ] Documentação da API
- [ ] Deploy em cloud (AWS/Azure)

---

## 🛠️ Stack Tecnológica

### **Backend / AI**
- ![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python) - Linguagem principal
- ![OpenCV](https://img.shields.io/badge/OpenCV-4.13-red?logo=opencv) - Processamento de vídeo
- ![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.9-orange) - Deteção de pontos faciais (468 landmarks)
- ![NumPy](https://img.shields.io/badge/NumPy-2.2-green?logo=numpy) - Operações matriciais
- ![SciPy](https://img.shields.io/badge/SciPy-1.15-blue?logo=scipy) - Cálculo de distâncias euclidianas
- **FastAPI/Flask** *(próximo)* - API REST

### **Frontend**
- **React** ou **HTML/CSS/JS** *(próximo)* - Interface do utilizador
- **WebRTC** *(futuro)* - Streaming de vídeo em tempo real

### **DevOps** *(futuro)*
- Docker - Containerização
- GitHub Actions - CI/CD
- AWS/Azure - Cloud deployment

---

## 🚀 Instalação e Execução

### **Pré-requisitos**

- Python 3.10 ou superior
- Webcam funcional
- Windows 10/11, macOS ou Linux

### **Instalação**

```bash
# 1. Clonar o repositório
git clone https://github.com/your-team/biotrust.git
cd biotrust

# 2. Criar ambiente virtual com Python 3.10
py -3.10 -m venv venv310

# 3. Ativar o ambiente virtual
# Windows (PowerShell):
.\venv310\Scripts\Activate.ps1

# Linux/macOS:
source venv310/bin/activate

# 4. Instalar dependências
pip install opencv-python mediapipe numpy scipy
```

### **Execução**

```bash
# Dentro do ambiente virtual:
python upg_iter_mesh_test_v3.py

# Ou diretamente:
.\venv310\Scripts\python.exe upg_iter_mesh_test_v3.py
```

### **Como Usar**

1. A janela da webcam vai abrir
2. **Fase 1:** Pisque os olhos **3 vezes** 👁️
3. **Fase 2:** Vire a cabeça para **ESQUERDA** ⬅️ e volte ao centro
4. **Fase 3:** Vire a cabeça para **DIREITA** ➡️ e volte ao centro
5. ✅ **Liveness Confirmado!**

**Para sair:**
- Pressionar **ESC**
- Clicar no **X** da janela

---

## 🧠 Como Funciona

### **1. Eye Aspect Ratio (EAR)**

O EAR mede o quão aberto está o olho baseado nas distâncias entre 6 pontos faciais:

```
EAR = (|P2-P6| + |P3-P5|) / (2 * |P1-P4|)
```

- **Olho aberto:** EAR ≈ 0.3
- **Olho fechado:** EAR < 0.18

### **2. Deteção de Rotação (Yaw)**

Medimos a distância do nariz até cada olho:

```
Razão de Simetria = distância(nariz → olho_esquerdo) / distância(nariz → olho_direito)
```

- **Frontal:** 0.85 < razão < 1.15
- **Esquerda:** razão > 2.05
- **Direita:** razão < 0.45

### **3. Sistema Sequencial Anti-Replay**

Ao contrário de sistemas simples, exigimos **3 ações em sequência**:
1. Piscar → 2. Esquerda → 3. Direita

Isto **impede ataques de replay** (vídeos gravados) porque cada sessão é única.

---

## 🗺️ Roadmap

### **Fase 1: MVP (48h Hackathon)** ✅ 50% Completo
- [x] Active Liveness Detection
- [ ] Motor de Risco básico
- [ ] Interface web simples
- [ ] Dashboard de simulação

### **Fase 2: Produto Completo** (Pós-Hackathon)
- [ ] Passive Liveness (rPPG)
- [ ] API REST documentada
- [ ] Integração com gateway de pagamento (Stripe/Moloni)
- [ ] Testes de segurança

### **Fase 3: Escala** (Futuro)
- [ ] Machine Learning para deteção de anomalias
- [ ] Suporte multi-idioma
- [ ] App móvel (iOS/Android)
- [ ] Certificações de segurança (ISO 27001)

---

## 👥 Equipa

**TecStorm '26 - Team BioTrust**

| Nome | Função | Área |
|------|--------|------|
| **João Evaristo** | Team Leader | Engenharia Informática |
| **Jordão Wiezel** | Developer | Engenharia Informática |
| **Anna Demenchuk** | Developer | Engenharia Informática |
| **Joana Du** | Scientific Consultant | Bioquímica |

---

## 📈 Objetivos de Desenvolvimento Sustentável (ODS)

- **ODS 9:** Indústria, Inovação e Infraestrutura
- **ODS 16:** Paz, Justiça e Instituições Eficazes (combate à fraude)

---

## 📝 Licença

Este projeto está sob a licença [MIT](LICENSE).

---

## 🔗 Links Úteis

- [Documentação MediaPipe Face Mesh](https://google.github.io/mediapipe/solutions/face_mesh.html)
- [OpenCV Documentation](https://docs.opencv.org/)
- [Artigo Original sobre EAR](http://vision.fe.uni-lj.si/cvww2016/proceedings/papers/05.pdf)

---

<div align="center">

**Feito com 💙 pela equipa BioTrust no TecStorm '26**

*Protegendo pagamentos digitais com biometria inteligente*

</div>
