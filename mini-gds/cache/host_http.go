package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"time"

	ac "availability-cache"
)

// httpHost asks the airline host service for seats. A host that fails to answer gives an error;
// one that does not know the class answers 404, which is zero seats.
type httpHost struct {
	baseURL string
	client  *http.Client
}

func newHTTPHost(baseURL string) *httpHost {
	return &httpHost{baseURL: baseURL, client: &http.Client{Timeout: 2 * time.Second}}
}

func (h *httpHost) Seats(key ac.Key) (int, error) {
	target := fmt.Sprintf("%s/flights/%s/classes/%s/seats",
		h.baseURL, url.PathEscape(key.Flight), url.PathEscape(key.Class))
	resp, err := h.client.Get(target)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusNotFound {
		return 0, nil // the host answered that it does not sell this class: no seats
	}
	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("status %d for %s", resp.StatusCode, target)
	}
	var body struct {
		Seats int `json:"seats"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		return 0, err
	}
	return body.Seats, nil
}
