// Chat functionality for DazCAD
// Initialize chat interface
function initChat() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendChatButton');
    
    // Handle send button click
    sendButton.addEventListener('click', sendChatMessage);
    
    // Handle enter key in chat input
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    // Add welcome message
    addChatMessage('system', 'AI Assistant ready! Ask me to modify your CadQuery code.');
}

function addChatMessage(role, content, timestamp = null) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = content;
    
    if (timestamp) {
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-timestamp';
        timeDiv.textContent = timestamp;
        messageDiv.appendChild(timeDiv);
    }
    
    messageDiv.appendChild(bubble);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageDiv;
}

function addLoadingMessage() {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message assistant';
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = '<div class="message-loading"></div> Thinking...';
    
    messageDiv.appendChild(bubble);
    chatMessages.appendChild(messageDiv);
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageDiv;
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendChatButton');
    const userMessage = chatInput.value.trim();
    
    if (!userMessage) return;
    
    // Add user message to chat
    addChatMessage('user', userMessage, new Date().toLocaleTimeString());
    
    // Clear input and disable send button
    chatInput.value = '';
    sendButton.disabled = true;
    chatInput.disabled = true;
    
    // Add loading message
    const loadingMessage = addLoadingMessage();
    
    try {
        const currentCode = codeEditor.getValue();
        
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: userMessage,
                code: currentCode
            })
        });
        
        const result = await response.json();
        
        // Remove loading message
        loadingMessage.remove();
        
        if (result.success) {
            // Add assistant response
            addChatMessage('assistant', result.response, new Date().toLocaleTimeString());
            
            // Update code if new code was provided (handles both new_code and code fields)
            const newCode = result.code || result.new_code;
            if (newCode && newCode !== currentCode) {
                codeEditor.setValue(newCode);
                addChatMessage('system', 'Code updated successfully!');
                
                // If new objects were generated, update the viewer
                if (result.run_result && result.run_result.objects) {
                    clearScene();
                    result.run_result.objects.forEach(obj => {
                        loadSTL(obj.stl, obj.name, obj.color, obj.transform);
                    });
                } else if (result.objects) {
                    // Fallback for backward compatibility
                    clearScene();
                    result.objects.forEach(obj => {
                        loadSTL(obj.stl, obj.name, obj.color, obj.transform);
                    });
                }
            }
        } else {
            // Add assistant response
            addChatMessage('assistant', result.response || `Sorry, I encountered an error: ${result.error}`, new Date().toLocaleTimeString());
            
            // If there are multiple errors from retry attempts, show them
            if (result.all_errors && result.all_errors.length > 1) {
                addChatMessage('system', 'I made multiple attempts to fix the code. You can check the browser console for details.');
                console.log('LLM retry attempts:', result.all_errors);
            }
        }
    } catch (error) {
        // Remove loading message
        loadingMessage.remove();
        addChatMessage('assistant', `Network error: ${error.message}`, new Date().toLocaleTimeString());
    } finally {
        // Re-enable input
        sendButton.disabled = false;
        chatInput.disabled = false;
        chatInput.focus();
    }
}