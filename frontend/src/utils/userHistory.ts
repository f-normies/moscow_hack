interface UserHistory {
  email: string;
  fullName: string;
  lastLogin: string;
  jobTitle?: string;
  avatar?: string;
}

const USER_HISTORY_KEY = 'user_history';
const MAX_HISTORY_ITEMS = 3;

export class UserHistoryService {
  /**
   * Save user login to history
   */
  static saveUserLogin(user: { email: string; full_name?: string }): void {
    try {
      const history = this.getUserHistory();
      const newEntry: UserHistory = {
        email: user.email,
        fullName: user.full_name || user.email.split('@')[0],
        lastLogin: new Date().toISOString(),
        jobTitle: 'Medical Professional', // Default placeholder
      };

      // Remove existing entry for this user
      const filteredHistory = history.filter(item => item.email !== user.email);

      // Add new entry at the beginning
      const updatedHistory = [newEntry, ...filteredHistory].slice(0, MAX_HISTORY_ITEMS);

      localStorage.setItem(USER_HISTORY_KEY, JSON.stringify(updatedHistory));
    } catch (error) {
      console.warn('Failed to save user history:', error);
    }
  }

  /**
   * Get user history sorted by last login
   */
  static getUserHistory(): UserHistory[] {
    try {
      const historyJson = localStorage.getItem(USER_HISTORY_KEY);
      if (!historyJson) return [];

      const history: UserHistory[] = JSON.parse(historyJson);
      return history.sort((a, b) => new Date(b.lastLogin).getTime() - new Date(a.lastLogin).getTime());
    } catch (error) {
      console.warn('Failed to load user history:', error);
      return [];
    }
  }

  /**
   * Clear all user history (for privacy)
   */
  static clearHistory(): void {
    try {
      localStorage.removeItem(USER_HISTORY_KEY);
    } catch (error) {
      console.warn('Failed to clear user history:', error);
    }
  }

  /**
   * Remove specific user from history
   */
  static removeUser(email: string): void {
    try {
      const history = this.getUserHistory();
      const filteredHistory = history.filter(item => item.email !== email);
      localStorage.setItem(USER_HISTORY_KEY, JSON.stringify(filteredHistory));
    } catch (error) {
      console.warn('Failed to remove user from history:', error);
    }
  }

  /**
   * Format relative time for display
   */
  static formatLastLogin(lastLogin: string): string {
    try {
      const date = new Date(lastLogin);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays} days ago`;
      if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
      return date.toLocaleDateString();
    } catch (error) {
      return 'Recently';
    }
  }
}

export type { UserHistory };