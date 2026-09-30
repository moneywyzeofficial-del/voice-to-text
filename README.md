# 🌿 Voz & Horas — Gestor Diário de Trabalho

Aplicação móvel e desktop de notas de voz com inteligência artificial, que transcreve o áudio, captura a localização GPS e organiza as tuas notas e tarefas automaticamente por **hora** e por **tema** (Jardins, Piscinas, Compras, Clientes).

---

## ✨ Funcionalidades Principais

* 🎙️ **Gravação de Voz Rápida:** Botão grande de gravação tátil no telemóvel e computador.
* 🕒 **Organização por Horas:** Registo automático da hora e data de cada nota, criando uma linha do tempo do teu dia.
* 📍 **Localização GPS:** Deteta automaticamente a morada aproximada onde estás a trabalhar.
* 🤖 **Inteligência Artificial (Gemini Flash):**
  * Transcrição fiel em Português Europeu.
  * Classificação automática por tema (*Jardinagem*, *Piscinas*, *Compras*, *Clientes*).
  * Extração de listas de tarefas e materiais pendentes.
* 📅 **Resumo Diário Inteligente:** Gera um relatório executivo do dia pronto a copiar e partilhar.
* 📱 **PWA para iPhone:** Pode ser adicionada diretamente ao ecrã principal do iPhone como uma aplicação nativa.

---

## 🚀 Como Iniciar

1. Executa o ficheiro `start.bat` ou corre no terminal:
   ```bash
   python run.py
   ```
2. O terminal vai mostrar o link e um **QR Code**.
3. No **iPhone**:
   * Liga-te à mesma rede Wi-Fi do computador.
   * Aponta a câmara do iPhone ao QR Code ou abre o Safari no endereço indicado.
   * No Safari, toca no botão **Partilhar** (ícone do quadrado com a seta para cima) e escolhe **"Adicionar ao Ecrã Principal"**.

---

## 🔑 Configurar a Chave de API do Gemini

1. Obtém uma chave gratuita em [Google AI Studio](https://aistudio.google.com).
2. Na app, toca no ícone de **Definições ⚙️** e cola a tua chave.
