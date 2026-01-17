'use client';

import { useState, useEffect } from 'react';
import { Bell, BellOff, X, CheckCircle, AlertCircle, Image } from 'lucide-react';
import {
  requestNotificationPermission,
  onForegroundMessage,
  getNotificationPermission,
} from '@/lib/firebase';
import { cn } from '@/lib/utils';

interface Notification {
  id: string;
  title: string;
  body: string;
  type?: string;
  timestamp: Date;
  read: boolean;
  data?: Record<string, string>;
}

// Toast component for notifications
function Toast({ title, body, onClose }: { title: string; body: string; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className="fixed bottom-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-4 z-50 max-w-sm animate-in slide-in-from-bottom-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
          <Bell className="w-4 h-4 text-primary-600" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-900 text-sm">{title}</p>
          <p className="text-gray-500 text-sm mt-1">{body}</p>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [permissionStatus, setPermissionStatus] = useState<string>('default');
  const [isRequesting, setIsRequesting] = useState(false);
  const [toast, setToast] = useState<{ title: string; body: string } | null>(null);

  // Check permission status on mount
  useEffect(() => {
    setPermissionStatus(getNotificationPermission());
  }, []);

  // Set up foreground message listener
  useEffect(() => {
    if (permissionStatus !== 'granted') return;

    const unsubscribe = onForegroundMessage((payload) => {
      const newNotification: Notification = {
        id: Date.now().toString(),
        title: payload.title,
        body: payload.body,
        type: payload.data?.type,
        timestamp: new Date(),
        read: false,
        data: payload.data,
      };

      setNotifications((prev) => [newNotification, ...prev].slice(0, 20));

      // Show toast notification
      setToast({ title: payload.title, body: payload.body });
    });

    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [permissionStatus]);

  const handleEnableNotifications = async () => {
    setIsRequesting(true);
    try {
      await requestNotificationPermission();
      setPermissionStatus(getNotificationPermission());
    } catch (error) {
      console.error('Failed to enable notifications:', error);
    } finally {
      setIsRequesting(false);
    }
  };

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const clearNotification = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  const getNotificationIcon = (type?: string) => {
    switch (type) {
      case 'render_complete':
        return <Image className="w-4 h-4 text-green-600" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-600" />;
      default:
        return <CheckCircle className="w-4 h-4 text-primary-600" />;
    }
  };

  return (
    <>
      {/* Toast Notification */}
      {toast && (
        <Toast
          title={toast.title}
          body={toast.body}
          onClose={() => setToast(null)}
        />
      )}

      <div className="relative">
        {/* Bell Button */}
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className="relative p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          {permissionStatus === 'granted' ? (
            <Bell className="w-5 h-5" />
          ) : (
            <BellOff className="w-5 h-5 text-gray-400" />
          )}

          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>

        {/* Dropdown */}
        {showDropdown && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setShowDropdown(false)}
            />

            {/* Dropdown Content */}
            <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                <h3 className="font-semibold text-gray-900">Notifications</h3>
                {notifications.length > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-sm text-primary-600 hover:text-primary-700"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              {/* Enable Notifications Prompt */}
              {permissionStatus !== 'granted' && (
                <div className="p-4 bg-gray-50 border-b border-gray-100">
                  <p className="text-sm text-gray-600 mb-3">
                    Enable notifications to get updates when your renders are ready.
                  </p>
                  <button
                    onClick={handleEnableNotifications}
                    disabled={isRequesting || permissionStatus === 'denied'}
                    className={cn(
                      'w-full px-4 py-2 text-sm font-medium rounded-lg transition-colors',
                      permissionStatus === 'denied'
                        ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                        : 'bg-primary-600 text-white hover:bg-primary-700'
                    )}
                  >
                    {isRequesting
                      ? 'Requesting...'
                      : permissionStatus === 'denied'
                      ? 'Notifications Blocked'
                      : 'Enable Notifications'}
                  </button>
                  {permissionStatus === 'denied' && (
                    <p className="text-xs text-gray-500 mt-2">
                      Please enable notifications in your browser settings.
                    </p>
                  )}
                </div>
              )}

              {/* Notification List */}
              <div className="max-h-96 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="p-8 text-center">
                    <Bell className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                    <p className="text-gray-500 text-sm">No notifications yet</p>
                  </div>
                ) : (
                  notifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={cn(
                        'flex items-start gap-3 p-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors',
                        !notification.read && 'bg-primary-50/50'
                      )}
                      onClick={() => markAsRead(notification.id)}
                    >
                      <div className="flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                        {getNotificationIcon(notification.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 text-sm">
                          {notification.title}
                        </p>
                        <p className="text-gray-500 text-sm mt-0.5 line-clamp-2">
                          {notification.body}
                        </p>
                        <p className="text-gray-400 text-xs mt-1">
                          {formatTimestamp(notification.timestamp)}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          clearNotification(notification.id);
                        }}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}

function formatTimestamp(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;

  return date.toLocaleDateString();
}
