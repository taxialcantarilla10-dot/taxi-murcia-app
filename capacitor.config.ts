import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'es.taximurcia.app',
  appName: 'Taxi Murcia',
  webDir: 'www',

  server: {
    androidScheme: 'https'
  },

  plugins: {
    SplashScreen: {
      launchShowDuration: 0
    },

    Geolocation: {
      permissions: [
        'location',
        'coarseLocation'
      ]
    }
  },

  android: {
    backgroundColor: '#f5f8f7'
  }
};

export default config;
