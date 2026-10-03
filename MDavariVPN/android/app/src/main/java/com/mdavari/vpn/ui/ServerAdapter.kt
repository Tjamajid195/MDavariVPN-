package com.mdavari.vpn.ui

import android.content.Context
import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.BaseAdapter
import android.widget.TextView
import com.mdavari.vpn.R
import com.mdavari.vpn.model.Server

/** آداپتر لیست سرورها (ListView). */
class ServerAdapter(private val ctx: Context) : BaseAdapter() {

    private val all = ArrayList<Server>()
    private val shown = ArrayList<Server>()
    private var onlyAlive = false
    private var countryFilter: String? = null
    var connectedKey: String? = null
        set(value) {
            field = value
            notifyDataSetChanged()
        }

    fun setData(list: List<Server>) {
        all.clear()
        all.addAll(list)
        rebuild()
    }

    fun data(): List<Server> = all

    fun setOnlyAlive(value: Boolean) {
        onlyAlive = value
        rebuild()
    }

    fun setCountry(value: String?) {
        countryFilter = value
        rebuild()
    }

    fun countries(): List<String> {
        val set = sortedSetOf<String>()
        for (s in all) {
            val fa = s.countryFa
            if (fa.isNotEmpty() && fa != "نامشخص") set.add(fa)
        }
        return set.toList()
    }

    private fun rebuild() {
        shown.clear()
        for (s in all) {
            if (onlyAlive && s.alive != true) continue
            if (countryFilter != null && s.countryFa != countryFilter) continue
            shown.add(s)
        }
        shown.sortWith(compareBy({ it.latency ?: 9e9 }, { it.pingMs ?: 99999 }))
        notifyDataSetChanged()
    }

    override fun getCount(): Int = shown.size
    override fun getItem(position: Int): Any = shown[position]
    override fun getItemId(position: Int): Long = position.toLong()

    override fun getView(position: Int, convertView: View?, parent: ViewGroup?): View {
        val view = convertView ?: LayoutInflater.from(ctx)
            .inflate(R.layout.item_server, parent, false)
        val s = shown[position]

        val txtStatus = view.findViewById<TextView>(R.id.txtRowStatus)
        val txtHost = view.findViewById<TextView>(R.id.txtRowHost)
        val txtPing = view.findViewById<TextView>(R.id.txtRowPing)
        val txtCountry = view.findViewById<TextView>(R.id.txtRowCountry)

        val isCurrent = connectedKey != null && s.key == connectedKey
        txtStatus.text = when {
            isCurrent -> "● متصل"
            s.alive == true -> "فعال"
            s.alive == false -> "بی‌پاسخ"
            else -> "—"
        }
        txtStatus.setTextColor(
            when {
                isCurrent -> Color.parseColor("#F5A623")
                s.alive == true -> Color.parseColor("#2ECC71")
                else -> Color.parseColor("#8C9AB4")
            }
        )
        txtHost.text = s.label
        txtCountry.text = s.countryFa
        txtPing.text = s.pingText
        txtPing.setTextColor(
            if (s.latency != null) Color.parseColor("#3AA0D8") else Color.parseColor("#8C9AB4")
        )
        return view
    }
}
