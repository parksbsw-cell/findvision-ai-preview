package ai.findvision.alert

import android.content.Context
import android.graphics.BitmapFactory
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.Gravity
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.io.File

object OverlayPopup {
    private val main = Handler(Looper.getMainLooper())
    private var current: android.view.View? = null
    private var manager: WindowManager? = null

    fun show(context: Context, message: String, image: File?, status: String) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(context)) return
        main.post {
            runCatching {
                current?.let { manager?.removeView(it) }
                val density = context.resources.displayMetrics.density
                fun dp(value: Int) = (value * density).toInt()
                val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
                manager = windowManager
                val close = Button(context).apply { text = "닫기" }
                val card = LinearLayout(context).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(dp(18), dp(16), dp(18), dp(18))
                    background = GradientDrawable().apply {
                        setColor(0xffffffff.toInt())
                        cornerRadius = dp(20).toFloat()
                        setStroke(dp(1), 0xffe5e7eb.toInt())
                    }
                    elevation = dp(14).toFloat()
                }
                val header = LinearLayout(context).apply { gravity = Gravity.CENTER_VERTICAL }
                header.addView(TextView(context).apply {
                    text = "📱 실종 재난문자"
                    textSize = 20f
                    setTextColor(0xff202235.toInt())
                }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
                header.addView(close)
                card.addView(header)
                card.addView(TextView(context).apply {
                    text = message
                    textSize = 16f
                    setTextColor(0xff242424.toInt())
                    setPadding(0, dp(12), 0, dp(12))
                })
                card.addView(TextView(context).apply {
                    text = status
                    textSize = 13f
                    setTextColor(0xff52525b.toInt())
                    setPadding(0, dp(4), 0, dp(10))
                })
                if (image != null && image.isFile) {
                    card.addView(TextView(context).apply {
                        text = "FindVision AI 참고 이미지"
                        textSize = 17f
                        setTextColor(0xff202235.toInt())
                        setPadding(0, dp(8), 0, dp(8))
                    })
                    card.addView(ImageView(context).apply {
                        setImageBitmap(BitmapFactory.decodeFile(image.absolutePath))
                        adjustViewBounds = true
                        scaleType = ImageView.ScaleType.FIT_CENTER
                        contentDescription = "재난문자 아래에 표시된 인상착의 참고 이미지"
                    }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
                    card.addView(TextView(context).apply {
                        text = "실제 인물 확인용이 아닌 참고 이미지입니다."
                        textSize = 12f
                        setPadding(0, dp(8), 0, 0)
                    })
                }
                val scroller = ScrollView(context).apply { addView(card) }
                close.setOnClickListener { runCatching { windowManager.removeView(scroller) }; if (current === scroller) current = null }
                val params = WindowManager.LayoutParams(
                    (context.resources.displayMetrics.widthPixels - dp(28)).coerceAtLeast(dp(260)),
                    (context.resources.displayMetrics.heightPixels * 0.86f).toInt(),
                    WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                    WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                        WindowManager.LayoutParams.FLAG_DIM_BEHIND,
                    PixelFormat.TRANSLUCENT
                ).apply {
                    gravity = Gravity.CENTER
                    dimAmount = 0.28f
                    windowAnimations = android.R.style.Animation_Dialog
                }
                windowManager.addView(scroller, params)
                current = scroller
            }
        }
    }
}
