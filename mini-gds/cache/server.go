package main

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"

	ac "availability-cache"
)

type offerKey struct {
	Flight string `json:"flight"`
	Class  string `json:"class"`
}

func (o offerKey) key() ac.Key { return ac.Key{Flight: o.Flight, Class: o.Class} }

type washResponse struct {
	Shown           []offerKey `json:"shown"`
	OpenWrongCaught int        `json:"open_wrong_caught"`
}

// server exposes the availability cache over HTTP.
type server struct {
	host ac.Host
	ttl  time.Duration
	now  func() time.Time

	mu    sync.RWMutex
	cache *ac.Cache
}

func newServer(host ac.Host, ttl time.Duration, now func() time.Time) *server {
	return &server{host: host, ttl: ttl, now: now, cache: ac.New(ttl, host, now)}
}

func (s *server) routes() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("GET /availability", s.availability)
	mux.HandleFunc("POST /updates", s.update)
	mux.HandleFunc("POST /wash", s.wash)
	mux.HandleFunc("POST /admin/reset", s.reset)
	return mux
}

func (s *server) current() *ac.Cache {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.cache
}

func (s *server) availability(w http.ResponseWriter, r *http.Request) {
	flight, class := r.URL.Query().Get("flight"), r.URL.Query().Get("class")
	if flight == "" || class == "" {
		http.Error(w, "flight and class are required", http.StatusBadRequest)
		return
	}
	key := ac.Key{Flight: flight, Class: class}
	seats, err := s.current().Availability(key)
	if err != nil {
		// Not "closed": the caller must know the host did not answer. The cache stored nothing,
		// so the next request asks again.
		log.Printf("host: %v; no answer for %s %s", err, flight, class)
		http.Error(w, "the host cannot answer", http.StatusServiceUnavailable)
		return
	}
	writeJSON(w, map[string]int{"seats": seats})
}

func (s *server) update(w http.ResponseWriter, r *http.Request) {
	var body struct {
		offerKey
		Seats int `json:"seats"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	s.current().Update(body.key(), body.Seats)
	w.WriteHeader(http.StatusNoContent)
}

func (s *server) wash(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Offers []offerKey `json:"offers"`
		Top    int        `json:"top"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	keys := make([]ac.Key, len(body.Offers))
	for i, offer := range body.Offers {
		keys[i] = offer.key()
	}
	kept, caught := ac.Wash(keys, body.Top, s.host)

	resp := washResponse{Shown: []offerKey{}, OpenWrongCaught: caught}
	for _, key := range kept {
		resp.Shown = append(resp.Shown, offerKey{Flight: key.Flight, Class: key.Class})
	}
	writeJSON(w, resp)
}

func (s *server) reset(w http.ResponseWriter, _ *http.Request) {
	s.mu.Lock()
	s.cache = ac.New(s.ttl, s.host, s.now)
	s.mu.Unlock()
	w.WriteHeader(http.StatusNoContent)
}

func writeJSON(w http.ResponseWriter, value any) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(value)
}
