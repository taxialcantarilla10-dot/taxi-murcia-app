from pathlib import Path

root = Path('android/app/src/main')
pkg = root / 'java/es/taximurcia/app'
pkg.mkdir(parents=True, exist_ok=True)
(pkg/'TaxiLocationService.java').write_text(r'''package es.taximurcia.app;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.location.*;
import android.os.*;
import androidx.core.app.NotificationCompat;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;

/** Real foreground location publisher. Credentials are supplied by the authenticated WebView
 * through the plugin and kept only in this app's private preferences. */
public class TaxiLocationService extends Service implements LocationListener {
    public static final String ACTION_UPDATE_AUTH = "es.taximurcia.app.UPDATE_AUTH";
    public static final String EXTRA_URL = "url", EXTRA_KEY = "key", EXTRA_TOKEN = "token", EXTRA_DRIVER = "driver";
    private static final String CHANNEL = "taxi_location";
    private static final int NOTIFICATION_ID = 1001;
    private LocationManager locationManager;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private Location lastLocation;
    private boolean busy;
    private boolean publishing;
    private String url, key, token, driverId;
    private long lastPublished;
    private boolean locationRequested;
    private final Runnable publishLoop = new Runnable() { public void run() {
        if (!publishing) publishLocation();
        handler.postDelayed(this, busy ? 5000L : 20000L);
    }};

    @Override public void onCreate() {
        super.onCreate(); loadAuth(); createChannel();
        Notification n = new NotificationCompat.Builder(this, CHANNEL)
            .setContentTitle("Taxi Murcia").setContentText("Seguimiento GPS activo durante el turno")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation).setOngoing(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE).build();
        if (Build.VERSION.SDK_INT >= 29) startForeground(NOTIFICATION_ID, n, 8); else startForeground(NOTIFICATION_ID, n);
        startUpdates(); handler.post(publishLoop);
    }
    private void loadAuth() { android.content.SharedPreferences p=getSharedPreferences("location_auth", MODE_PRIVATE); url=p.getString(EXTRA_URL, null); key=p.getString(EXTRA_KEY, null); token=p.getString(EXTRA_TOKEN, null); driverId=p.getString(EXTRA_DRIVER, null); }
    public void updateAuth(Intent i) { if(i==null)return; url=i.getStringExtra(EXTRA_URL); key=i.getStringExtra(EXTRA_KEY); token=i.getStringExtra(EXTRA_TOKEN); driverId=i.getStringExtra(EXTRA_DRIVER); getSharedPreferences("location_auth", MODE_PRIVATE).edit().putString(EXTRA_URL,url).putString(EXTRA_KEY,key).putString(EXTRA_TOKEN,token).putString(EXTRA_DRIVER,driverId).apply(); startUpdates(); publishLocation(); }
    private void createChannel() { if(Build.VERSION.SDK_INT>=26){ NotificationChannel c=new NotificationChannel(CHANNEL,"Seguimiento GPS",NotificationManager.IMPORTANCE_LOW); c.setDescription("Ubicación activa del taxi"); getSystemService(NotificationManager.class).createNotificationChannel(c); } }
    private void startUpdates() {
        if (Build.VERSION.SDK_INT >= 23 && checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)!=PackageManager.PERMISSION_GRANTED) {
            // The WebView may start the service while Android's permission dialog is still open.
            // Do not give up permanently: retry after the user grants foreground location.
            if (!locationRequested) { locationRequested=true; handler.postDelayed(() -> { locationRequested=false; startUpdates(); }, 2000L); }
            return;
        }
        locationRequested=false;
        locationManager=(LocationManager)getSystemService(Context.LOCATION_SERVICE);
        try { locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000L, 0f, this, Looper.getMainLooper()); } catch(Exception ignored) {}
        try { locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 5000L, 0f, this, Looper.getMainLooper()); } catch(Exception ignored) {}
        try { Location l=locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER); if(l!=null)lastLocation=l; } catch(Exception ignored) {}
    }
    @Override public void onLocationChanged(Location l) { if(l!=null) lastLocation=l; }
    private void publishLocation() {
        if(lastLocation==null || token==null || driverId==null || url==null || publishing)return;
        final Location l=new Location(lastLocation); final long now=System.currentTimeMillis();
        publishing=true; io.execute(() -> { try {
            // Re-evaluate service state on every tick: 5 seconds while active, 20 seconds otherwise.
            busy = hasActiveService();
            JSONObject d=new JSONObject(); d.put("driver_id",driverId).put("latitude",l.getLatitude()).put("longitude",l.getLongitude());
            if(l.hasAccuracy())d.put("accuracy_m",l.getAccuracy()); if(l.hasBearing())d.put("heading",l.getBearing()); if(l.hasSpeed())d.put("speed_mps",l.getSpeed());
            d.put("availability","available").put("updated_at",new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'",java.util.Locale.US).format(new java.util.Date(now)));
            request("POST", url+"/rest/v1/driver_locations?on_conflict=driver_id", d.toString(), "resolution=merge-duplicates");
            JSONObject driverPayload=new JSONObject(d.toString()); driverPayload.remove("driver_id");
            driverPayload.put("location_updated_at",driverPayload.getString("updated_at"));
            request("PATCH", url+"/rest/v1/drivers?id=eq."+URLEncoder.encode(driverId,"UTF-8"), driverPayload.toString(), null);
            lastPublished=now;
        } catch(Exception ignored) {} finally { publishing=false; }});
    }
    private boolean hasActiveService() { try { String out=request("GET",url+"/rest/v1/services?select=id&driver_id=eq."+URLEncoder.encode(driverId,"UTF-8")+"&status=in.(accepted,arriving,arrived,picked_up)&limit=1",null,null); return out!=null && out.trim().length()>2 && !out.trim().equals("[]"); } catch(Exception e){ return busy; } }
    private String request(String method,String endpoint,String body,String prefer) throws Exception { HttpURLConnection c=(HttpURLConnection)new URL(endpoint).openConnection(); c.setRequestMethod(method); c.setRequestProperty("apikey",key); c.setRequestProperty("Authorization","Bearer "+token); c.setRequestProperty("Content-Type","application/json"); if(prefer!=null)c.setRequestProperty("Prefer",prefer); c.setConnectTimeout(10000);c.setReadTimeout(10000); if(body!=null){c.setDoOutput(true);try(OutputStream o=c.getOutputStream()){o.write(body.getBytes(StandardCharsets.UTF_8));}} int code=c.getResponseCode(); InputStream in=code>=400?c.getErrorStream():c.getInputStream(); if(in==null)return ""; try(BufferedReader r=new BufferedReader(new InputStreamReader(in,StandardCharsets.UTF_8))){StringBuilder s=new StringBuilder();String x;while((x=r.readLine())!=null)s.append(x);return code>=400?null:s.toString();} finally {c.disconnect();} }
    @Override public void onProviderEnabled(String p){} @Override public void onProviderDisabled(String p){} @Override public void onStatusChanged(String p,int s,Bundle b){}
    @Override public int onStartCommand(Intent i,int flags,int id){ if(i!=null && ACTION_UPDATE_AUTH.equals(i.getAction()))updateAuth(i); return START_STICKY; }
    @Override public void onDestroy(){publishing=false;handler.removeCallbacks(publishLoop);if(locationManager!=null)locationManager.removeUpdates(this);io.shutdownNow();super.onDestroy();}
    @Override public IBinder onBind(Intent i){return null;}
}
''')
(pkg/'ForegroundLocationPlugin.java').write_text(r'''package es.taximurcia.app;
import android.content.Intent;
import android.os.Build;
import android.os.PowerManager;
import android.provider.Settings;
import android.net.Uri;
import com.getcapacitor.*;
import com.getcapacitor.annotation.CapacitorPlugin;
import org.json.JSONObject;

@CapacitorPlugin(name="ForegroundLocation")
public class ForegroundLocationPlugin extends Plugin {
 @PluginMethod public void start(PluginCall call){
  String token=call.getString("accessToken"), driver=call.getString("driverId"), url=call.getString("supabaseUrl"), key=call.getString("supabaseKey");
  if(token==null||driver==null||url==null||key==null){call.reject("Faltan credenciales de sesión");return;}
  Intent i=new Intent(getContext(),TaxiLocationService.class).setAction(TaxiLocationService.ACTION_UPDATE_AUTH).putExtra(TaxiLocationService.EXTRA_TOKEN,token).putExtra(TaxiLocationService.EXTRA_DRIVER,driver).putExtra(TaxiLocationService.EXTRA_URL,url).putExtra(TaxiLocationService.EXTRA_KEY,key);
  if(Build.VERSION.SDK_INT>=23){PowerManager pm=(PowerManager)getContext().getSystemService(android.content.Context.POWER_SERVICE);if(pm!=null&&!pm.isIgnoringBatteryOptimizations(getContext().getPackageName())){try{Intent b=new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:"+getContext().getPackageName()));getContext().startActivity(b);}catch(Exception ignored){}}}
  if(Build.VERSION.SDK_INT>=26)getContext().startForegroundService(i);else getContext().startService(i); call.resolve();
 }
 @PluginMethod public void refreshAuth(PluginCall call){start(call);}
 @PluginMethod public void stop(PluginCall call){getContext().stopService(new Intent(getContext(),TaxiLocationService.class));call.resolve();}
}
''')
manifest=root/'AndroidManifest.xml'; s=manifest.read_text()
if 'android.permission.ACCESS_FINE_LOCATION' not in s:
 s=s.replace('<application','<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />\n    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />\n    <uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />\n    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />\n    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />\n    <uses-permission android:name="android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" />\n    <application',1)
if 'TaxiLocationService' not in s:s=s.replace('</application>','<service android:name=".TaxiLocationService" android:exported="false" android:foregroundServiceType="location" />\n    </application>')
manifest.write_text(s)
main=pkg/'MainActivity.java'; s=main.read_text()
if 'registerPlugin(ForegroundLocationPlugin.class)' not in s:
 s=s.replace('import com.getcapacitor.BridgeActivity;','import com.getcapacitor.BridgeActivity;\nimport android.Manifest;\nimport android.content.pm.PackageManager;\nimport android.os.Build;\nimport android.os.Bundle;\nimport android.view.WindowManager;')
 s=s.replace('public class MainActivity extends BridgeActivity {','''public class MainActivity extends BridgeActivity {
 @Override public void onCreate(Bundle state){super.onCreate(state);getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);registerPlugin(ForegroundLocationPlugin.class);if(Build.VERSION.SDK_INT>=23)requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION,Manifest.permission.POST_NOTIFICATIONS},410);} 
 @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results){super.onRequestPermissionsResult(request,permissions,results);if(request==410&&Build.VERSION.SDK_INT>=29&&checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{Manifest.permission.ACCESS_BACKGROUND_LOCATION},411);}''')
 main.write_text(s)
print('Native location publisher patched')
