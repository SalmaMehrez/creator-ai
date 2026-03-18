const API_URL = "/api";

let state = {
    title: '',
    style: '',
    idea: '',
    length: '',
    audience: '',
    chatHistory: [],
    structure: [],
    finalScript: ''
};

// Theme Toggle Logic
function toggleTheme() {
    const htmlEl = document.documentElement;
    const currentTheme = htmlEl.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    htmlEl.setAttribute('data-theme', newTheme);

    // Change icon
    const themeBtn = document.getElementById('theme-btn');
    themeBtn.textContent = newTheme === 'dark' ? '☀️' : '🌙';
}

function switchStep(fromId, toId) {
    const fromEl = document.getElementById(fromId);
    const toEl = document.getElementById(toId);

    fromEl.style.opacity = '0';
    fromEl.style.transform = 'translateY(-20px)';

    setTimeout(() => {
        fromEl.classList.remove('active-step');
        fromEl.classList.add('hidden-step');

        toEl.classList.remove('hidden-step');
        toEl.classList.add('active-step');

        // Trigger reflow
        void toEl.offsetWidth;

        toEl.style.opacity = '1';
        toEl.style.transform = 'translateY(0)';
    }, 400);
}

function startCreation() {
    switchStep('step-landing', 'step-idea');
}

function startIdeation() {
    state.title = document.getElementById('video-title').value;
    state.style = document.getElementById('video-style').value;
    state.idea = document.getElementById('video-idea').value;
    state.length = document.getElementById('video-length').value;
    state.audience = document.getElementById('video-audience').value;

    if (!state.title || !state.idea || !state.length) {
        alert("Please enter a title, a brief concept, and select a length.");
        return;
    }

    switchStep('step-idea', 'step-chat');

    // Simulate initial AI greeting based on user input
    setTimeout(() => {
        addChatMessage(`Great! I've noted that your video is a ${state.style || 'video'} titled "${state.title}" with a target length of ${state.length} minutes. To make an impactful script, what is the main problem this video solves for your audience?`, 'ai');
    }, 600);
}

function addChatMessage(text, sender) {
    const chatBox = document.getElementById('chat-box');
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender}`;
    bubble.textContent = text;
    chatBox.appendChild(bubble);
    chatBox.scrollTop = chatBox.scrollHeight;

    if (sender === 'user') {
        state.chatHistory.push({ role: 'user', content: text });
    } else {
        state.chatHistory.push({ role: 'assistant', content: text });
    }
}

async function sendChatMessage() {
    const inputEl = document.getElementById('chat-input-text');
    const text = inputEl.value.trim();
    if (!text) return;

    addChatMessage(text, 'user');
    inputEl.value = '';

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: state.title,
                context: `Style: ${state.style}\nIdea: ${state.idea}\nLength: ${state.length} minutes\nAudience: ${state.audience}`,
                history: state.chatHistory
            })
        });
        const data = await response.json();
        addChatMessage(data.reply, 'ai');
    } catch (e) {
        console.error("API Error:", e);
        // Fallback mockup
        setTimeout(() => {
            addChatMessage("Noted. One last question: what is the Call to Action (CTA) at the end of the video? (Subscribe, link in description, etc.)", 'ai');
        }, 1000);
    }
}

async function proceedToStructure() {
    switchStep('step-chat', 'step-structure');

    const editorEl = document.getElementById('structure-editor');
    editorEl.innerHTML = '<p style="text-align:center;">Generating structure...</p>';

    try {
        const response = await fetch(`${API_URL}/generate_structure`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                history: state.chatHistory
            })
        });
        const data = await response.json();
        state.structure = data.structure;
    } catch (e) {
        console.error("Structure API Error:", e);
        // Mock fallback
        state.structure = [
            { title: "🎬 Hook (0:00 - 0:15)", content: "Strong hook on the problem mentioned in the discussion." },
            { title: "👋 Introduction (0:15 - 0:45)", content: "Quick introduction and promise of the video." },
            { title: "📖 Body - Part 1", content: "Explanation of the main concept with an example." },
            { title: "🧠 Body - Part 2", content: "Advanced technique or secret tip." },
            { title: "🎯 Conclusion & CTA", content: "Quick summary and clear call to action." }
        ];
    }

    renderStructure();
}

function renderStructure() {
    const editorEl = document.getElementById('structure-editor');
    editorEl.innerHTML = '';

    state.structure.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'structure-item';
        div.innerHTML = `
            <input type="text" value="${item.title}" class="structure-title-input" onchange="updateStructureTitle(${index}, this.value)" style="width: 100%; font-size: 1.1em; font-weight: bold; margin-bottom: 0.5rem; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: var(--text-color); padding: 0.5rem; border-radius: 8px;">
            <textarea rows="4" onchange="updateStructureContent(${index}, this.value)" style="width: 100%; padding: 0.8rem; background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(255, 255, 255, 0.1); color: var(--text-color); border-radius: 8px; resize: vertical;">${item.content}</textarea>
        `;
        editorEl.appendChild(div);
    });
}

function updateStructureTitle(index, value) {
    state.structure[index].title = value;
}

function updateStructureContent(index, value) {
    state.structure[index].content = value;
}

function formatScriptContent(text) {
    // Basic formatting: replace newlines with <br>
    let formattedText = text.replace(/\n\n/g, '<br><br>');
    formattedText = formattedText.replace(/\n(?!\<br\>)/g, '<br>');

    // Format [TAGS]
    formattedText = formattedText.replace(/\[(.*?)\]/g, '<span class="section-tag">$1</span><br>');

    // Format **Bold Text** as Headings or Bold
    formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Format ## Headings
    formattedText = formattedText.replace(/### (.*?)(<br>|$)/g, '<h3>$1</h3>');
    formattedText = formattedText.replace(/## (.*?)(<br>|$)/g, '<h3>$1</h3>');

    return formattedText;
}

async function generateScript() {
    switchStep('step-structure', 'step-script');

    const scriptEl = document.getElementById('final-script');
    scriptEl.innerHTML = "Generating script...\nThis may take a minute.";

    try {
        const response = await fetch(`${API_URL}/generate_script`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                structure: state.structure
            })
        });
        const data = await response.json();
        state.finalScript = data.script;
        scriptEl.innerHTML = formatScriptContent(state.finalScript);
    } catch (e) {
        console.error("Script API Error:", e);
        setTimeout(() => {
            state.finalScript = `[HOOK]\nHey! Have you always wanted to learn Python but thought it takes too long? What if I told you that in 30 days, you can go from zero to building your first app?\n\n[INTRO]\nWelcome to this new video. I'm excited to have you here...\n\n(This is a locally generated demo script)`;
            scriptEl.innerHTML = formatScriptContent(state.finalScript);
        }, 2000);
    }
}

async function addVisualIdeas() {
    const scriptEl = document.getElementById('final-script');
    const visualsBtn = document.getElementById('btn-visuals');
    
    // Save current script just in case
    const currentScriptText = scriptEl.innerText;
    
    visualsBtn.disabled = true;
    visualsBtn.innerHTML = 'Generating... <span style="font-size: 0.8em">⏳</span>';
    scriptEl.innerHTML = "Generating visual ideas...\nThis may take a minute.";

    try {
        console.log("Sending script for visuals:", state.finalScript || currentScriptText);
        const response = await fetch(`${API_URL}/generate_visuals`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                script: state.finalScript || currentScriptText
            })
        });
        const data = await response.json();
        console.log("Received visual data:", data);
        
        // Update the script element with the new script including visuals
        state.finalScript = data.script_with_visuals;
        scriptEl.innerHTML = formatScriptContent(state.finalScript);
        
        visualsBtn.innerHTML = 'Visuals Added ✨';
        
    } catch (e) {
        console.error("Visuals API Error:", e);
        setTimeout(() => {
            state.finalScript = `[B-Roll: Coding montage]\n[HOOK]\nHey! Have you always wanted to learn Python but thought it takes too long? What if I told you that in 30 days, you can go from zero to building your first app?\n\n[Text on screen: "30 Days Challenge!"]\n[INTRO]\nWelcome to this new video. I'm excited to have you here...\n\n(This is a locally generated demo visual script)`;
            scriptEl.innerHTML = formatScriptContent(state.finalScript);
            visualsBtn.innerHTML = 'Visuals Added ✨';
            visualsBtn.disabled = false;
        }, 2000);
    }
}

function copyScript() {
    const scriptEl = document.getElementById('final-script');
    navigator.clipboard.writeText(scriptEl.innerText).then(() => {
        alert('Script copied to clipboard!');
    });
}

function exportPDF() {
    const { jsPDF } = window.jspdf;
    const pdfBtn = document.getElementById('btn-pdf');

    // Feedback to user
    pdfBtn.disabled = true;
    pdfBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" class="icon"><path d="M12 16l-4-4h3V4h2v8h3l-4 4z" fill="currentColor"/><path d="M4 18h16v2H4v-2z" fill="currentColor"/></svg> Exporting...`;

    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

    const margin = 18;
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const contentWidth = pageWidth - margin * 2;
    let cursorY = margin;

    // ── Header band ──────────────────────────────────────────────
    doc.setFillColor(99, 102, 241); // indigo
    doc.rect(0, 0, pageWidth, 22, 'F');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(16);
    doc.setTextColor(255, 255, 255);
    doc.text('Creator AI — YouTube Script', margin, 14);

    // Date (right aligned in header)
    const dateStr = new Date().toLocaleDateString('fr-FR', { day: '2-digit', month: 'long', year: 'numeric' });
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text(dateStr, pageWidth - margin, 14, { align: 'right' });

    cursorY = 32;

    // ── Video title ───────────────────────────────────────────────
    if (state.title) {
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(14);
        doc.setTextColor(40, 40, 40);
        const titleLines = doc.splitTextToSize(`📹 ${state.title}`, contentWidth);
        doc.text(titleLines, margin, cursorY);
        cursorY += titleLines.length * 7 + 4;

        // Separator line
        doc.setDrawColor(200, 200, 200);
        doc.line(margin, cursorY, pageWidth - margin, cursorY);
        cursorY += 8;
    }

    // ── Script body ───────────────────────────────────────────────
    const scriptEl = document.getElementById('final-script');
    const rawText = scriptEl.innerText || '';
    const lines = rawText.split('\n');

    doc.setFontSize(10.5);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(30, 30, 30);

    const lineHeight = 5.8;

    for (const line of lines) {
        const trimmed = line.trim();

        // Section tags or headings → styled bold indigo
        if (/^\[.*\]$/.test(trimmed) || /^#{1,3} /.test(trimmed) || /^\*\*.*\*\*$/.test(trimmed)) {
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(99, 102, 241);
            doc.setFontSize(11);
        } else {
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(30, 30, 30);
            doc.setFontSize(10.5);
        }

        const wrappedLines = doc.splitTextToSize(trimmed || ' ', contentWidth);

        for (const wl of wrappedLines) {
            if (cursorY + lineHeight > pageHeight - margin) {
                doc.addPage();
                // Thin header on subsequent pages
                doc.setFillColor(99, 102, 241);
                doc.rect(0, 0, pageWidth, 10, 'F');
                doc.setFont('helvetica', 'italic');
                doc.setFontSize(8);
                doc.setTextColor(255, 255, 255);
                doc.text('Creator AI — YouTube Script', margin, 7);
                cursorY = 18;
                // Restore text style
                if (/^\[.*\]$/.test(trimmed) || /^#{1,3} /.test(trimmed)) {
                    doc.setFont('helvetica', 'bold');
                    doc.setTextColor(99, 102, 241);
                    doc.setFontSize(11);
                } else {
                    doc.setFont('helvetica', 'normal');
                    doc.setTextColor(30, 30, 30);
                    doc.setFontSize(10.5);
                }
            }
            doc.text(wl, margin, cursorY);
            cursorY += lineHeight;
        }
    }

    // ── Footer on last page ───────────────────────────────────────
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(8);
    doc.setTextColor(160, 160, 160);
    doc.text('Generated with Creator AI', pageWidth / 2, pageHeight - 8, { align: 'center' });

    // ── Save ──────────────────────────────────────────────────────
    const safeName = (state.title || 'script').replace(/[^a-z0-9]/gi, '_').toLowerCase();
    doc.save(`${safeName}_script.pdf`);

    pdfBtn.disabled = false;
    pdfBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" class="icon"><path d="M12 16l-4-4h3V4h2v8h3l-4 4z" fill="currentColor"/><path d="M4 18h16v2H4v-2z" fill="currentColor"/></svg> Export PDF`;
}

function resetApp() {
    state = { title: '', style: '', idea: '', length: '', audience: '', chatHistory: [], structure: [], finalScript: '' };
    document.getElementById('video-title').value = '';
    document.getElementById('video-style').value = '';
    document.getElementById('video-idea').value = '';
    document.getElementById('video-length').value = '';
    document.getElementById('video-audience').value = '';
    document.getElementById('chat-box').innerHTML = '';
    switchStep('step-script', 'step-landing');
}
