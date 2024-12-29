import React, { useState } from 'react';
import axios from 'axios';
import './ChatWidget.css';
import { useEffect, useRef } from 'react';
import { FaPaperPlane, FaImage } from 'react-icons/fa'; // For arrow and image icons

const ChatWidget = () => {
    const [messages, setMessages] = useState([]);
    const [userMessage, setUserMessage] = useState('');
    const [image, setImage] = useState(null); // To handle image upload
    const chatBodyRef = useRef(null);

    useEffect(() => {
        if (chatBodyRef.current) {
            chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSendMessage = async () => {
        if (userMessage.trim() === '' && !image) return;
    
        const newMessage = { role: 'user', content: userMessage };
        setMessages([...messages, newMessage]);
        setUserMessage('');
    
        const formData = new FormData();
        if (userMessage.trim()) formData.append('text', userMessage);
        if (image) formData.append('image', image);
    
        try {
            const response = await axios.post(window.location.protocol+'//'+window.location.hostname+':5000/generate-response', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
    
            const botMessage = response.data.response
                ? { role: 'assistant', content: response.data.response }
                : { role: 'assistant', content: 'Sorry, I did not understand your request.' };
            setMessages((prevMessages) => [...prevMessages, botMessage]);
        } catch (error) {
            const errorMessage = { role: 'assistant', content: 'An error occurred while processing your request.' };
            setMessages((prevMessages) => [...prevMessages, errorMessage]);
        }
    
        setImage(null); // Clear the uploaded image after sending
    };
     

    const handleImageUpload = (e) => {
        setImage(e.target.files[0]);
    };

    const getMessage = (msg, index) => {
        var response = msg.content.split('\n');
        return (
            <div key={index} className={`message ${msg.role}`}>
                {response.map((responseItem, i) => (
                    <p key={i}>{responseItem}</p>
                ))}
            </div>
        );
    };

    return (
        <div className="chat-widget">
            <div className="chat-header">DoctHers Chatbot</div>
            <div className="chat-body" ref={chatBodyRef}>
                {messages.map(getMessage)}
            </div>
            <div className="chat-footer">
                <input
                    type="file"
                    accept="image/*"
                    style={{ display: 'none' }}
                    id="upload-button"
                    onChange={handleImageUpload}
                />
                <label htmlFor="upload-button" className="image-upload-button">
                    <FaImage />
                </label>
                <input
                    type="text"
                    placeholder="Type your message..."
                    value={userMessage}
                    onChange={(e) => setUserMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                />
                <button onClick={handleSendMessage}>
                    <FaPaperPlane />
                </button>
            </div>
        </div>
    );
};

export default ChatWidget;
