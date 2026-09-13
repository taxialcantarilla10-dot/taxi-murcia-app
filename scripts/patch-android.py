from pathlib import Path

root = Path('android/app/src/main')
pkg = root / 'java/es/taximurcia/app'
pkg.mkdir(parents=True, exist_ok=True)
(pkg/'TaxiLocationService.java').write_text(r'''package es.taximurcia.app;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Build;
import android.os.Bundle;
import android.os.IBinder;
import androidx.core.app.NotificationCompat;

public class TaxiLocationService extends Service implements LocationListener {
    private static final String CHANNEL = "taxi_location";
    private static final int NOTIFICATION_ID = 1001;
    private LocationManager locationManager;
    @Override public void onCreate() {
        super.onCreate(); createChannel();
        Notification n = new NotificationCompat.Builder(this, CHANNEL).setContentTitle("Taxi Murcia").setContentText("Seguimiento GPS activo durante el turno").setSmallIcon(android.R.drawable.ic_menu_mylocation).setOngoing(true).setCategory(NotificationCompat.CATEGORY_SERVICE).build();
        if (Build.VERSION.SDK_INT >= 29) startForeground(NOTIFICATION_ID, n, 8); else startForeground(NOTIFICATION_ID, n);
        startUpdates();
    }
    private void createChannel() { if (Build.VERSION.SDK_INT >= 26) { NotificationChannel c = new NotificationChannel(CHANNEL, "Seguimiento GPS", NotificationManager.IMPORTANCE_LOW); c.setDescription("Indica que la ubicación de Taxi Murcia está activa"); getSystemService(NotificationManager.class).createNotificationChannel(c); } }
    private void startUpdates() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) return;
        locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
        try { locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 5000L, 5f, this); } catch (Exception ignored) {}
        try { locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 10000L, 10f, this); } catch (Exception ignored) {}
    }
    @Override public void onLocationChanged(Location location) { }
    @Override public void onProviderEnabled(String provider) { }
    @Override public void onProviderDisabled(String provider) { }
    @Override public void onStatusChanged(String provider, int status, Bundle extras) { }
    @Override public int onStartCommand(Intent intent, int flags, int startId) { return START_STICKY; }
    @Override public void onDestroy() { if (locationManager != null) locationManager.removeUpdates(this); super.onDestroy(); }
    @Override public IBinder onBind(Intent intent) { return null; }
}
''')
(pkg/'ForegroundLocationPlugin.java').write_text(r'''package es.taximurcia.app;
import android.content.Intent;
import android.os.Build;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.JSObject;
@CapacitorPlugin(name = "ForegroundLocation")
public class ForegroundLocationPlugin extends Plugin {
    @com.getcapacitor.PluginMethod public void start(PluginCall call) { Intent i = new Intent(getContext(), TaxiLocationService.class); if (Build.VERSION.SDK_INT >= 26) getContext().startForegroundService(i); else getContext().startService(i); call.resolve(new JSObject().put("active", true)); }
    @com.getcapacitor.PluginMethod public void stop(PluginCall call) { getContext().stopService(new Intent(getContext(), TaxiLocationService.class)); call.resolve(new JSObject().put("active", false)); }
}
''')
manifest = root/'AndroidManifest.xml'
s = manifest.read_text()
s = s.replace('<application', '<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />\n    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />\n    <uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />\n    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />\n    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n    <application', 1)
s = s.replace('</application>', '        <service android:name=".TaxiLocationService" android:exported="false" android:foregroundServiceType="location" />\n    </application>')
manifest.write_text(s)
main = pkg/'MainActivity.java'
s = main.read_text()
s = s.replace('import com.getcapacitor.BridgeActivity;', 'import com.getcapacitor.BridgeActivity;\nimport android.Manifest;\nimport android.content.Intent;\nimport android.os.Build;\nimport android.os.Bundle;\nimport android.view.WindowManager;')
s = s.replace('public class MainActivity extends BridgeActivity {', '''public class MainActivity extends BridgeActivity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state); getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON); registerPlugin(ForegroundLocationPlugin.class);
        if (Build.VERSION.SDK_INT >= 23) requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION, Manifest.permission.POST_NOTIFICATIONS}, 410);
        if (Build.VERSION.SDK_INT >= 29) requestPermissions(new String[]{Manifest.permission.ACCESS_BACKGROUND_LOCATION}, 411);
        Intent i = new Intent(this, TaxiLocationService.class); if (Build.VERSION.SDK_INT >= 26) startForegroundService(i); else startService(i);
    }''')
main.write_text(s)
print('Android foreground location files and manifest written')
