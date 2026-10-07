package ai.findvision.alert

import android.Manifest
import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.ComponentName
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.view.ViewGroup
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : Activity() {
    private lateinit var apiUrl: EditText
    private lateinit var accessKey: EditText
    private lateinit var enabled: CheckBox
    private lateinit var status: TextView
    private val prefs by lazy { getSharedPreferences(PREFS, MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        createChannel()
        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(22), dp(20), dp(28))
        }
        page.addView(TextView(this).apply {
            text = "🔎 FindVision AI 재난문자 알림"
            textSize = 23f
            setTextColor(0xff202235.toInt())
        })
        page.addView(TextView(this).apply {
            text = "Android 알림 접근을 사용해 실종 관련 재난문자를 감지합니다. 알림을 감지하면 원문 팝업을 먼저 띄우고, AI 생성이 끝나면 같은 팝업의 문자 아래에 참고 이미지를 표시합니다."
            textSize = 15f
            setPadding(0, dp(14), 0, dp(14))
        })
        page.addView(label("FindVision 모바일 API 주소 (HTTPS)"))
        apiUrl = EditText(this).apply {
            hint = "https://your-api.example.com"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            setSingleLine(true)
            setText(prefs.getString(KEY_URL, ""))
        }
        page.addView(apiUrl, match())
        page.addView(label("팀 앱 연결 코드"))
        accessKey = EditText(this).apply {
            hint = "서버 관리자가 별도로 전달한 연결 코드"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            setSingleLine(true)
            setText(prefs.getString(KEY_ACCESS, ""))
        }
        page.addView(accessKey, match())
        page.addView(TextView(this).apply {
            text = "문자 원문과 추출된 인상착의는 이미지 생성을 위해 설정된 Cloudflare AI로 전송됩니다. 서버는 원문이나 이미지를 DB에 저장하지 않으며, 생성 처리 중에만 메모리에 보관합니다. 결과 이미지는 이 기기에 저장됩니다."
            textSize = 13f
            setPadding(0, dp(12), 0, dp(8))
        })
        enabled = CheckBox(this).apply {
            text = "동의하고 자동 분석 사용"
            isChecked = prefs.getBoolean(KEY_ENABLED, false)
        }
        page.addView(enabled)
        page.addView(action("1. 문자 알림 접근 권한 설정") {
            saveSettings()
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        })
        page.addView(action("2. 팝업 표시 권한 설정") {
            saveSettings()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                startActivity(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
            }
        })
        page.addView(action("3. 시스템 알림 권한 요청") {
            if (Build.VERSION.SDK_INT >= 33) {
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 20)
            }
        })
        page.addView(action("설정 저장 및 상태 새로고침") {
            saveSettings()
            updateStatus()
        })
        status = TextView(this).apply { textSize = 14f; setPadding(0, dp(12), 0, dp(6)) }
        page.addView(status)
        page.addView(TextView(this).apply {
            text = "감지는 휴대전화가 재난문자 앱의 알림을 FindVision AI에 전달할 때 작동합니다. 제조사·OS 설정에 따라 일부 셀 브로드캐스트가 알림으로 전달되지 않을 수 있고, 방해금지 모드·배터리 절약 설정은 팝업을 늦출 수 있습니다. 이 앱은 SMS 읽기 권한을 요구하지 않습니다."
            textSize = 12f
            setPadding(0, dp(8), 0, 0)
        })
        setContentView(ScrollView(this).apply { addView(page) })
        updateStatus()
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 20)
        }
    }

    override fun onResume() { super.onResume(); if (::status.isInitialized) updateStatus() }

    private fun saveSettings() {
        val url = apiUrl.text.toString().trim().trimEnd('/')
        val code = accessKey.text.toString().trim()
        val valid = url.startsWith("https://") && code.length >= 20
        val consent = enabled.isChecked && valid
        prefs.edit().putString(KEY_URL, url).putString(KEY_ACCESS, code)
            .putBoolean(KEY_ENABLED, consent).apply()
        if (!valid && enabled.isChecked) enabled.isChecked = false
    }

    private fun updateStatus() {
        val component = ComponentName(this, DisasterNotificationListener::class.java)
        val enabledListeners = Settings.Secure.getString(contentResolver, "enabled_notification_listeners") ?: ""
        val listenerReady = enabledListeners.split(':').any { it.equals(component.flattenToString(), true) }
        val overlayReady = Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(this)
        val serviceReady = prefs.getBoolean(KEY_ENABLED, false) && prefs.getString(KEY_URL, "").orEmpty().startsWith("https://")
        status.text = "자동 분석: ${if (serviceReady) "동의됨" else "꺼짐"}\n" +
            "문자 알림 접근: ${if (listenerReady) "허용됨" else "설정 필요"}\n" +
            "문자 아래 이미지 팝업: ${if (overlayReady) "허용됨" else "설정 필요"}"
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val channel = NotificationChannel(CHANNEL_ID, "실종 재난문자 이미지", NotificationManager.IMPORTANCE_HIGH).apply {
                description = "실종 관련 재난문자 원문과 AI 참고 이미지 알림"
                lockscreenVisibility = NotificationManager.VISIBILITY_PRIVATE
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun action(text: String, callback: () -> Unit) = Button(this).apply {
        this.text = text
        setOnClickListener { callback() }
    }
    private fun label(text: String) = TextView(this).apply { this.text = text; textSize = 14f; setPadding(0, dp(12), 0, dp(4)) }
    private fun match() = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    companion object {
        const val PREFS = "findvision_settings"
        const val KEY_URL = "api_url"
        const val KEY_ACCESS = "access_key"
        const val KEY_ENABLED = "auto_enabled"
        const val CHANNEL_ID = "findvision_alerts"
    }
}
