/**
 * Firebase configuration and push notification service
 */

import { initializeApp, getApps, FirebaseApp } from 'firebase/app';
import { getMessaging, getToken, onMessage, Messaging } from 'firebase/messaging';

// Firebase configuration - these should be set via environment variables
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

// Initialize Firebase
let app: FirebaseApp | null = null;
let messaging: Messaging | null = null;

export function getFirebaseApp(): FirebaseApp | null {
  if (typeof window === 'undefined') return null;

  if (!app && getApps().length === 0) {
    // Only initialize if config is available
    if (firebaseConfig.apiKey && firebaseConfig.projectId) {
      app = initializeApp(firebaseConfig);
    }
  } else if (!app) {
    app = getApps()[0];
  }

  return app;
}

export function getFirebaseMessaging(): Messaging | null {
  if (typeof window === 'undefined') return null;

  const firebaseApp = getFirebaseApp();
  if (!firebaseApp) return null;

  if (!messaging) {
    try {
      messaging = getMessaging(firebaseApp);
    } catch (error) {
      console.error('Failed to initialize Firebase Messaging:', error);
      return null;
    }
  }

  return messaging;
}

/**
 * Request permission and get FCM token
 */
export async function requestNotificationPermission(): Promise<string | null> {
  if (typeof window === 'undefined') return null;

  // Check if notifications are supported
  if (!('Notification' in window)) {
    console.warn('This browser does not support notifications');
    return null;
  }

  // Request permission
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    console.warn('Notification permission denied');
    return null;
  }

  const fcmMessaging = getFirebaseMessaging();
  if (!fcmMessaging) {
    console.error('Firebase Messaging not initialized');
    return null;
  }

  try {
    // Get FCM token
    const vapidKey = process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY;
    const token = await getToken(fcmMessaging, { vapidKey });

    if (token) {
      console.log('FCM Token:', token);
      // Send token to backend to associate with user/project
      await registerTokenWithBackend(token);
      return token;
    } else {
      console.warn('No registration token available');
      return null;
    }
  } catch (error) {
    console.error('Failed to get FCM token:', error);
    return null;
  }
}

/**
 * Register FCM token with backend
 */
async function registerTokenWithBackend(token: string): Promise<void> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  try {
    await fetch(`${apiUrl}/api/notifications/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });
  } catch (error) {
    console.error('Failed to register token with backend:', error);
  }
}

/**
 * Listen for foreground messages
 */
export function onForegroundMessage(
  callback: (payload: { title: string; body: string; data?: Record<string, string> }) => void
): (() => void) | null {
  const fcmMessaging = getFirebaseMessaging();
  if (!fcmMessaging) return null;

  const unsubscribe = onMessage(fcmMessaging, (payload) => {
    console.log('Foreground message received:', payload);

    callback({
      title: payload.notification?.title || 'ArchViz AI',
      body: payload.notification?.body || '',
      data: payload.data as Record<string, string> | undefined,
    });
  });

  return unsubscribe;
}

/**
 * Check if notifications are enabled
 */
export function areNotificationsEnabled(): boolean {
  if (typeof window === 'undefined') return false;
  if (!('Notification' in window)) return false;
  return Notification.permission === 'granted';
}

/**
 * Get current notification permission status
 */
export function getNotificationPermission(): NotificationPermission | 'unsupported' {
  if (typeof window === 'undefined') return 'unsupported';
  if (!('Notification' in window)) return 'unsupported';
  return Notification.permission;
}
