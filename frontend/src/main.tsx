import React from 'react';
import ReactDOM from 'react-dom/client';
import AuthenticatedApp from './AuthenticatedApp';
import './style.css';
import './pages.css';

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><AuthenticatedApp /></React.StrictMode>);
