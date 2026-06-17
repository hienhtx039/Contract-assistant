/**
 * GreenNode Interview Assistant — Frontend
 * Handles audio capture, WebSocket communication, and UI.
 */

let websocket = null;
let audioContext = null;
let audioWorklet = null;
let mediaStream = null;
let sessionId = null;
let timerInterval = null;
let startTime = null;
let transcriptSegments = [];     // latest batch from server (for display update)
let allCompletedSegments = [];   // ALL completed segments accumulated over entire interview
let wsReconnectAttempts = 0;
let cvFile = null;
let jdFile = null;
let jdExtractedText = "";

// ─── Drag & Drop Setup ──────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    setupDropZone("jd-drop", "jd-upload", handleJDUpload);
    setupDropZone("cv-drop", "cv-upload", handleCVUpload);
});

function setupDropZone(dropId, inputId, handler) {
    const zone = document.getElementById(dropId);

    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("dragover");
    });

    zone.addEventListener("dragleave", () => {
        zone.classList.remove("dragover");
    });

    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("dragover");
        const file = e.dataTransfer.files[0];
        if (!file) return;
        // Set file on the hidden input so handler works the same way
        const input = document.getElementById(inputId);
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        handler(input);
    });
}

// ─── Document Upload & Auto-fill ────────────────────────────────

async function handleCVUpload(input) {
    const file = input.files[0];
    if (!file) return;
    cvFile = file;
    document.getElementById("cv-filename").textContent = file.name;
    document.getElementById("cv-drop").classList.add("uploaded");
    checkGenerateReady();

    // Auto-extract candidate name
    setStatus("Extracting candidate name from CV...", "connecting");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", "cv");

    try {
        const resp = await fetch("/api/extract-info", { method: "POST", body: formData });
        const data = await resp.json();
        if (data.extracted) {
            document.getElementById("candidate-name").value = data.extracted;
            setStatus(`Candidate: ${data.extracted}`, "idle");
        } else {
            setStatus("CV uploaded. Please fill candidate name manually.", "idle");
        }
    } catch (err) {
        setStatus("CV uploaded. Fill candidate name manually.", "idle");
    }
}

async function handleJDUpload(input) {
    const file = input.files[0];
    if (!file) return;
    jdFile = file;
    document.getElementById("jd-filename").textContent = file.name;
    document.getElementById("jd-drop").classList.add("uploaded");
    checkGenerateReady();

    // Auto-extract position
    setStatus("Extracting position from JD...", "connecting");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", "jd");

    try {
        const resp = await fetch("/api/extract-info", { method: "POST", body: formData });
        const data = await resp.json();
        if (data.extracted) {
            document.getElementById("position").value = data.extracted;
            setStatus(`Position: ${data.extracted}`, "idle");
        } else {
            setStatus("JD uploaded. Please fill position manually.", "idle");
        }
        if (data.full_text) {
            jdExtractedText = data.full_text;
            // Also fill JD text area for reference
            if (!document.getElementById("jd-text").value.trim()) {
                document.getElementById("jd-text").value = data.full_text.substring(0, 500);
            }
        }
    } catch (err) {
        setStatus("JD uploaded. Fill position manually.", "idle");
    }
}

async function extractFromJDText() {
    const jdText = document.getElementById("jd-text").value.trim();
    if (!jdText) {
        alert("Please type JD text first.");
        return;
    }

    setStatus("Extracting position & skills from JD text...", "connecting");

    try {
        const resp = await fetch("/api/extract-jd-text", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jd_text: jdText }),
        });
        const data = await resp.json();

        if (data.position) {
            document.getElementById("position").value = data.position;
        }
        jdExtractedText = jdText;

        let msg = "";
        if (data.position) msg += `Position: ${data.position}`;
        if (data.functional_skills && data.functional_skills.length) {
            msg += ` | Skills: ${data.functional_skills.join(", ")}`;
            // Auto-fill vocabulary hints from skills
            const existingVocab = document.getElementById("vocab-hints").value.trim();
            if (!existingVocab) {
                document.getElementById("vocab-hints").value = data.functional_skills.join(", ");
            }
        }
        setStatus(msg || "Extracted from JD text.", "idle");
    } catch (err) {
        setStatus("Failed to extract from JD text.", "error");
    }
}

function checkGenerateReady() {
    document.getElementById("btn-generate-questions").disabled = !cvFile;
}

async function generateQuestions() {
    if (!cvFile) {
        alert("Please upload a CV first.");
        return;
    }

    const position = document.getElementById("position").value.trim();
    if (!position) {
        alert("Please fill in the Position field first.");
        return;
    }

    const btn = document.getElementById("btn-generate-questions");
    btn.disabled = true;
    btn.textContent = "Generating...";
    setStatus("Generating interview questions from CV + JD (30-60s)...", "assessing");

    const formData = new FormData();
    formData.append("file", cvFile);
    formData.append("position", position);

    if (jdFile) {
        formData.append("jd_file", jdFile);
    }
    const jdText = document.getElementById("jd-text").value.trim();
    if (jdText) {
        formData.append("jd_text", jdText);
    }

    try {
        const resp = await fetch("/api/generate-questions", {
            method: "POST",
            body: formData,
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "Failed to generate questions");
        }

        const questions = await resp.json();
        displayGeneratedQuestions(questions);
        setStatus("Interview questions generated! Ready to start interview.", "idle");
    } catch (err) {
        console.error("Question generation error:", err);
        setStatus(`Error: ${err.message}`, "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Generate Interview Questions from CV + JD";
    }
}

function displayGeneratedQuestions(q) {
    const container = document.getElementById("generated-questions");
    container.style.display = "block";

    let html = "";

    if (q.candidate_summary) {
        html += `<div class="q-summary"><strong>Tóm tắt ứng viên:</strong> ${escapeHtml(q.candidate_summary)}</div>`;
    }

    html += renderQuestionSection("Functional Skills", q.functional_skills, "skill_area");
    html += renderQuestionSection("GreenNode's DNA", q.greennode_dna, "criterion");
    html += renderQuestionSection("Motivation", q.motivation, "criterion");

    container.innerHTML = html;
}

function renderQuestionSection(title, items, labelKey) {
    if (!items || !items.length) return "";
    let html = `<h3>${escapeHtml(title)}</h3>`;
    for (const item of items) {
        const label = item[labelKey] || item.criterion || item.skill_area || "";
        html += `<div class="q-card">
            <div class="q-label">${escapeHtml(label)}</div>
            <div class="q-main">${escapeHtml(item.main_question)}</div>
            <div class="q-followup">↳ ${escapeHtml(item.follow_up)}</div>
            <div class="q-hint">${escapeHtml(item.what_to_look_for)}</div>
        </div>`;
    }
    return html;
}

// ─── Recording Controls ─────────────────────────────────────────

async function startRecording() {
    const candidateName = document.getElementById("candidate-name").value.trim();
    const interviewer = document.getElementById("interviewer").value.trim();
    const position = document.getElementById("position").value.trim();

    if (!candidateName || !interviewer || !position) {
        alert("Please fill in all interview setup fields.");
        return;
    }

    const wsUrl = document.getElementById("ws-url").value.trim();
    const language = document.getElementById("language").value;

    setStatus("Connecting to transcription server...", "connecting");

    try {
        // Create session on the interview API
        const resp = await fetch("/api/session", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                candidate_name: candidateName,
                interviewer: interviewer,
                position: position,
            }),
        });
        const data = await resp.json();
        sessionId = data.session_id;

        // Connect WebSocket to WhisperLive
        websocket = new WebSocket(wsUrl);
        websocket.onopen = () => {
            // Send initial config (WhisperLive protocol)
            const vocabHints = document.getElementById("vocab-hints").value.trim();
            const config = {
                uid: sessionId,
                language: language,
                task: "transcribe",
                model: "large-v3",
                use_vad: true,
                initial_prompt: vocabHints ? `Phỏng vấn về: ${vocabHints}` : undefined,
            };
            websocket.send(JSON.stringify(config));
            setStatus("Waiting for server...", "connecting");
        };

        websocket.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            handleServerMessage(msg);
        };

        websocket.onerror = (err) => {
            console.error("WebSocket error:", err);
            setStatus("Connection error. Attempting reconnect...", "error");
        };

        websocket.onclose = (event) => {
            // Don't reconnect if user clicked Stop or interview ended normally
            if (document.getElementById("btn-stop").disabled) {
                setStatus("Disconnected from server", "idle");
                return;
            }

            // Auto-reconnect on unexpected disconnect
            stopAudioCapture();
            const reconnectDelay = Math.min(3000, 1000 * (wsReconnectAttempts + 1));
            wsReconnectAttempts++;

            if (wsReconnectAttempts <= 5) {
                setStatus(`Connection lost. Reconnecting in ${reconnectDelay/1000}s... (attempt ${wsReconnectAttempts}/5)`, "error");
                setTimeout(() => {
                    console.log(`Reconnect attempt ${wsReconnectAttempts}`);
                    reconnectWebSocket(wsUrl, language);
                }, reconnectDelay);
            } else {
                setStatus("Connection lost after 5 attempts. Click Stop then Start to retry.", "error");
            }
        };
    } catch (err) {
        console.error("Failed to start:", err);
        setStatus(`Error: ${err.message}`, "error");
    }
}

function handleServerMessage(msg) {
    if (msg.message === "SERVER_READY") {
        wsReconnectAttempts = 0;  // Reset on successful connection
        if (allCompletedSegments.length === 0) {
            // Fresh recording
        }
        setStatus("Recording...", "recording");
        startAudioCapture();
        startTimer();

        document.getElementById("btn-start").disabled = true;
        document.getElementById("btn-stop").disabled = false;
        document.getElementById("btn-assess").disabled = true;
        return;
    }

    if (msg.message === "DISCONNECT") {
        stopRecording();
        return;
    }

    if (msg.status === "WAIT") {
        setStatus(`Server busy. Wait ~${Math.ceil(msg.message)} min.`, "connecting");
        return;
    }

    if (msg.language) {
        console.log(`Detected language: ${msg.language} (prob: ${msg.language_prob})`);
    }

    if (msg.segments) {
        updateTranscript(msg.segments);
    }
}

function stopRecording() {
    wsReconnectAttempts = 999;  // Prevent auto-reconnect on intentional stop
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        const encoder = new TextEncoder();
        websocket.send(encoder.encode("END_OF_AUDIO"));
        websocket.close();
    }

    stopAudioCapture();
    stopTimer();

    setStatus("Recording stopped. You can now generate assessment.", "idle");
    document.getElementById("btn-start").disabled = false;
    document.getElementById("btn-stop").disabled = true;
    document.getElementById("btn-assess").disabled = false;
    document.getElementById("btn-save-transcript").disabled = false;
}

function reconnectWebSocket(wsUrl, language) {
    try {
        websocket = new WebSocket(wsUrl);
        websocket.onopen = () => {
            const vocabHints = document.getElementById("vocab-hints").value.trim();
            const config = {
                uid: sessionId,
                language: language,
                task: "transcribe",
                model: "large-v3",
                use_vad: true,
                initial_prompt: vocabHints ? `Phỏng vấn về: ${vocabHints}` : undefined,
            };
            websocket.send(JSON.stringify(config));
        };
        websocket.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            handleServerMessage(msg);
        };
        websocket.onerror = (err) => {
            console.error("Reconnect WebSocket error:", err);
        };
        websocket.onclose = () => {
            if (document.getElementById("btn-stop").disabled) return;
            const delay = Math.min(3000, 1000 * (wsReconnectAttempts + 1));
            wsReconnectAttempts++;
            if (wsReconnectAttempts <= 5) {
                setStatus(`Reconnecting... (${wsReconnectAttempts}/5)`, "error");
                setTimeout(() => reconnectWebSocket(wsUrl, language), delay);
            } else {
                setStatus("Connection lost. Click Stop then Start to retry.", "error");
            }
        };
        startAudioCapture();
    } catch (err) {
        console.error("Reconnect failed:", err);
    }
}

// ─── Audio Capture ──────────────────────────────────────────────

async function startAudioCapture() {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
            },
        });

        audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(mediaStream);

        await audioContext.audioWorklet.addModule("audioprocessor.js");
        audioWorklet = new AudioWorkletNode(audioContext, "audio-processor");

        let audioChunkCount = 0;
        audioWorklet.port.onmessage = (event) => {
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(event.data.buffer);
                audioChunkCount++;
                if (audioChunkCount % 50 === 0) {
                    console.log(`Audio chunks sent: ${audioChunkCount}, buffer size: ${event.data.length}`);
                }
            }
        };

        source.connect(audioWorklet);
        audioWorklet.connect(audioContext.destination);
    } catch (err) {
        console.error("Audio capture error:", err);
        setStatus(`Microphone error: ${err.message}`, "error");
    }
}

function stopAudioCapture() {
    if (audioWorklet) {
        audioWorklet.disconnect();
        audioWorklet = null;
    }
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
        mediaStream = null;
    }
}

// ─── Transcript Display ─────────────────────────────────────────

function updateTranscript(segments) {
    transcriptSegments = segments;
    const container = document.getElementById("transcript");
    const prevCount = allCompletedSegments.length;

    // Accumulate completed segments (avoid duplicates by checking start time)
    for (const seg of segments) {
        if (seg.completed) {
            const exists = allCompletedSegments.some(
                (s) => s.start === seg.start && s.text === seg.text
            );
            if (!exists) {
                allCompletedSegments.push({ ...seg });
            }
        }
    }

    // Append-only: only add NEW completed segments to DOM (not full re-render)
    const newSegments = allCompletedSegments.slice(prevCount);

    // Remove placeholder if first segments
    if (prevCount === 0 && newSegments.length > 0) {
        container.innerHTML = "";
    }

    // Remove previous in-progress element
    const oldInProgress = container.querySelector(".segment.in-progress");
    if (oldInProgress) oldInProgress.remove();

    // Append new completed segments
    for (const seg of newSegments) {
        const div = document.createElement("div");
        div.className = "segment completed";
        div.innerHTML = `<span class="timestamp">[${formatTime(parseFloat(seg.start))}]</span>
            <span class="text">${escapeHtml(seg.text)}</span>`;
        container.appendChild(div);
    }

    // Append current in-progress segment
    const inProgress = segments.filter((s) => !s.completed);
    if (inProgress.length > 0) {
        const seg = inProgress[inProgress.length - 1];
        const div = document.createElement("div");
        div.className = "segment in-progress";
        div.innerHTML = `<span class="timestamp">[${formatTime(parseFloat(seg.start))}]</span>
            <span class="text">${escapeHtml(seg.text)}</span>`;
        container.appendChild(div);
    }

    // Show placeholder if empty
    if (allCompletedSegments.length === 0 && inProgress.length === 0) {
        container.innerHTML = '<p class="placeholder">Listening...</p>';
    }

    container.scrollTop = container.scrollHeight;

    // Update segment count
    const countEl = document.getElementById("segment-count");
    if (countEl) countEl.textContent = `${allCompletedSegments.length} segments`;
}

function getFullTranscript() {
    // Use ALL accumulated segments, not just latest batch
    return allCompletedSegments.map((s) => s.text.trim()).filter(Boolean).join(" ");
}

// ─── File Upload ────────────────────────────────────────────────

async function uploadAudioFile(input) {
    const file = input.files[0];
    if (!file) return;

    const language = document.getElementById("language").value;
    setStatus(`Uploading and transcribing "${file.name}"...`, "connecting");

    const vocabHints = document.getElementById("vocab-hints").value.trim();
    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);
    if (vocabHints) formData.append("vocab_hints", vocabHints);

    try {
        const resp = await fetch("/api/transcribe", {
            method: "POST",
            body: formData,
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "Transcription failed");
        }

        const result = await resp.json();
        const text = result.text || "";

        if (!text.trim()) {
            setStatus("No speech detected in the audio file.", "error");
            return;
        }

        // Display as a single completed segment
        transcriptSegments = [{ start: "0.000", end: "0.000", text: text, completed: true }];
        const container = document.getElementById("transcript");
        container.innerHTML = `<div class="segment completed">
            <span class="timestamp">[upload]</span>
            <span class="text">${escapeHtml(text)}</span>
        </div>`;

        setStatus(`Transcribed "${file.name}" successfully. You can now generate assessment.`, "idle");
        document.getElementById("btn-assess").disabled = false;
        document.getElementById("btn-save-transcript").disabled = false;
    } catch (err) {
        console.error("Upload error:", err);
        setStatus(`Upload error: ${err.message}`, "error");
    }

    // Reset file input so same file can be re-uploaded
    input.value = "";
}

// ─── Assessment ─────────────────────────────────────────────────

async function runAssessment() {
    const transcript = getFullTranscript();
    if (!transcript) {
        alert("No transcript available. Please record an interview first.");
        return;
    }

    const candidateName = document.getElementById("candidate-name").value.trim();
    const interviewer = document.getElementById("interviewer").value.trim();
    const position = document.getElementById("position").value.trim();

    setStatus("Running AI assessment (this may take 30-60 seconds)...", "assessing");
    document.getElementById("btn-assess").disabled = true;

    try {
        const resp = await fetch("/api/assess", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId || "manual",
                candidate_name: candidateName,
                interviewer: interviewer,
                position: position,
                transcript: transcript,
                jd_text: document.getElementById("jd-text").value.trim() || jdExtractedText,
                date: new Date().toISOString().split("T")[0],
            }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "Assessment failed");
        }

        const result = await resp.json();
        displayAssessment(result.assessment);

        // Show download button
        const dlBtn = document.getElementById("btn-download");
        dlBtn.style.display = "inline-block";
        dlBtn.disabled = false;
        dlBtn.dataset.url = result.excel_download;

        setStatus("Assessment complete! You can download the Excel file.", "idle");
    } catch (err) {
        console.error("Assessment error:", err);
        setStatus(`Assessment error: ${err.message}`, "error");
        document.getElementById("btn-assess").disabled = false;
    }
}

function displayAssessment(assessment) {
    const container = document.getElementById("assessment");

    const recClass = assessment.recommendation === "HIRE" ? "hire"
        : assessment.recommendation === "CONSIDER" ? "consider" : "not-proceed";

    let html = `
        <div class="assessment-header">
            <div class="total-score">
                <span class="score-value">${assessment.total_score?.toFixed(1) || "N/A"}</span>
                <span class="score-label">/ 5.0</span>
            </div>
            <div class="recommendation ${recClass}">
                ${assessment.recommendation || "N/A"}
            </div>
        </div>

        <div class="assessment-summary">
            <p>${escapeHtml(assessment.summary || "")}</p>
        </div>

        <h3>Functional Skills</h3>
        <table class="score-table">
            <tr><th>Criterion</th><th>Score</th><th>Evidence</th></tr>
            ${(assessment.functional_skills || []).map(s => `
                <tr>
                    <td>${escapeHtml(s.criterion)}</td>
                    <td class="score-cell">${s.score}</td>
                    <td>${escapeHtml(s.evidence)}</td>
                </tr>
            `).join("")}
        </table>

        <h3>GreenNode's DNA</h3>
        <table class="score-table">
            <tr><th>Criterion</th><th>Score</th><th>Evidence</th></tr>
            ${(assessment.greennode_dna || []).map(s => `
                <tr>
                    <td>${escapeHtml(s.criterion)}</td>
                    <td class="score-cell">${s.score}</td>
                    <td>${escapeHtml(s.evidence)}</td>
                </tr>
            `).join("")}
        </table>

        <h3>Motivation</h3>
        <table class="score-table">
            <tr><th>Criterion</th><th>Score</th><th>Evidence</th></tr>
            ${(assessment.motivation || []).map(s => `
                <tr>
                    <td>${escapeHtml(s.criterion)}</td>
                    <td class="score-cell">${s.score}</td>
                    <td>${escapeHtml(s.evidence)}</td>
                </tr>
            `).join("")}
        </table>
    `;

    container.innerHTML = html;
}

function saveTranscript() {
    const transcript = getFullTranscript();
    if (!transcript) {
        alert("No transcript to save.");
        return;
    }

    const candidateName = document.getElementById("candidate-name").value.trim() || "unknown";
    const position = document.getElementById("position").value.trim() || "";
    const interviewer = document.getElementById("interviewer").value.trim() || "";
    const dateStr = new Date().toISOString().split("T")[0];

    let content = `Candidate: ${candidateName}\n`;
    content += `Position: ${position}\n`;
    content += `Interviewer: ${interviewer}\n`;
    content += `Date: ${dateStr}\n`;
    content += `Segments: ${allCompletedSegments.length}\n`;
    content += "=".repeat(60) + "\n\n";

    for (const seg of allCompletedSegments) {
        const timeStr = formatTime(parseFloat(seg.start));
        content += `[${timeStr}] ${seg.text.trim()}\n`;
    }

    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transcript_${candidateName.replace(/\s+/g, "_")}_${dateStr}.txt`;
    a.click();
    URL.revokeObjectURL(url);

    setStatus("Transcript saved locally.", "idle");
}

function downloadExcel() {
    const btn = document.getElementById("btn-download");
    const url = btn.dataset.url;
    if (url) {
        window.open(url, "_blank");
    }
}

// ─── Timer ──────────────────────────────────────────────────────

function startTimer() {
    startTime = Date.now();
    const timerEl = document.getElementById("timer");
    timerEl.style.display = "block";

    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const h = String(Math.floor(elapsed / 3600)).padStart(2, "0");
        const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
        const s = String(elapsed % 60).padStart(2, "0");
        timerEl.textContent = `${h}:${m}:${s}`;
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

// ─── Utilities ──────────────────────────────────────────────────

function setStatus(text, state) {
    const el = document.getElementById("status");
    el.textContent = text;
    el.className = `status ${state}`;
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function escapeHtml(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function togglePanel(id) {
    const el = document.getElementById(id);
    el.classList.toggle("collapsed");
    const icon = el.previousElementSibling.querySelector(".toggle-icon");
    if (icon) {
        icon.textContent = el.classList.contains("collapsed") ? "+" : "-";
    }
}
