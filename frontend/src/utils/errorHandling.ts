import { notification } from 'antd';
import axios from 'axios';

export const handleApiError = (error: any, customMessage: string = 'Operation Failed') => {
  let description = 'An unexpected error occurred. Please try again.';

  if (axios.isAxiosError(error) && error.response) {
    const status = error.response.status;
    const data = error.response.data as any;
    
    if (data?.detail) {
      description = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    } else {
      switch (status) {
        case 404:
          description = 'The requested resource was not found.';
          break;
        case 500:
          description = 'A server error occurred. Please try again later.';
          break;
        case 501:
          description = 'This feature is not currently available or implemented.';
          break;
        case 403:
          description = 'You do not have permission to perform this action.';
          break;
      }
    }
  } else if (error.message) {
    if (error.message === 'Network Error') {
      description = 'Unable to connect to the server. Please check your internet connection.';
    } else {
      description = error.message;
    }
  }

  notification.error({
    message: customMessage,
    description,
    placement: 'bottomRight',
    duration: 6,
  });
};
