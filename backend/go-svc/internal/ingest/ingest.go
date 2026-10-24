// Package ingest 将外部收件渠道（WhatsApp / 企業微信）的消息转为标准作业输入。
// 当前为简化载荷；生产接入 WhatsApp Cloud API / 企業微信回調時在此适配真实报文。
package ingest

import (
	"encoding/json"
	"fmt"
	"strings"
)

// WhatsAppPayload WhatsApp webhook 的简化载荷。
type WhatsAppPayload struct {
	From     string `json:"from"`
	Text     string `json:"text"`
	Vertical string `json:"vertical,omitempty"`
}

// WeComPayload 企業微信回調的简化载荷。
type WeComPayload struct {
	From     string `json:"from"`
	Content  string `json:"content"`
	Vertical string `json:"vertical,omitempty"`
}

// Result 标准化收件结果。
type Result struct {
	From     string
	Text     string
	Vertical string
}

// ParseWhatsApp 解析 WhatsApp webhook 载荷，默认垂直场景为 insurance_hk。
func ParseWhatsApp(body []byte) (*Result, error) {
	var p WhatsAppPayload
	if err := json.Unmarshal(body, &p); err != nil {
		return nil, err
	}
	p.Text = strings.TrimSpace(p.Text)
	if p.Text == "" {
		return nil, fmt.Errorf("empty message text")
	}
	if p.Vertical == "" {
		p.Vertical = "insurance_hk"
	}
	return &Result{From: p.From, Text: p.Text, Vertical: p.Vertical}, nil
}

// ParseWeCom 解析企業微信回調載荷，默认垂直场景为 insurance_hk。
func ParseWeCom(body []byte) (*Result, error) {
	var p WeComPayload
	if err := json.Unmarshal(body, &p); err != nil {
		return nil, err
	}
	p.Content = strings.TrimSpace(p.Content)
	if p.Content == "" {
		return nil, fmt.Errorf("empty message content")
	}
	if p.Vertical == "" {
		p.Vertical = "insurance_hk"
	}
	return &Result{From: p.From, Text: p.Content, Vertical: p.Vertical}, nil
}
