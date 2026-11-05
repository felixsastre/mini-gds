package main

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	ac "availability-cache"
)

type fakeHost struct {
	seats map[ac.Key]int
	down  bool // the host cannot answer
	calls int
}

func (h *fakeHost) Seats(k ac.Key) (int, error) {
	h.calls++
	if h.down {
		return 0, errors.New("host down")
	}
	return h.seats[k], nil
}

var (
	m100 = ac.Key{Flight: "AA100", Class: "M"}
	k100 = ac.Key{Flight: "AA100", Class: "K"}
)

func newTestServer(host ac.Host) http.Handler {
	return newServer(host, time.Minute, time.Now).routes()
}

func do(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, target, strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestAvailabilityAsksTheHostOnceThenServesTheCache(t *testing.T) {
	host := &fakeHost{seats: map[ac.Key]int{m100: 4}}
	h := newTestServer(host)

	for range 2 {
		rec := do(t, h, "GET", "/availability?flight=AA100&class=M", "")
		if rec.Code != 200 || strings.TrimSpace(rec.Body.String()) != `{"seats":4}` {
			t.Fatalf("got %d %q", rec.Code, rec.Body.String())
		}
	}
	if host.calls != 1 {
		t.Errorf("host was asked %d times, want 1", host.calls)
	}
}

func TestAvailabilityNeedsFlightAndClass(t *testing.T) {
	h := newTestServer(&fakeHost{})
	if rec := do(t, h, "GET", "/availability?flight=AA100", ""); rec.Code != 400 {
		t.Errorf("status %d, want 400", rec.Code)
	}
}

func TestAnUpdateReplacesTheCopyWithoutAskingTheHost(t *testing.T) {
	host := &fakeHost{seats: map[ac.Key]int{m100: 0}}
	h := newTestServer(host)

	if rec := do(t, h, "POST", "/updates", `{"flight":"AA100","class":"M","seats":3}`); rec.Code != 204 {
		t.Fatalf("update status %d", rec.Code)
	}
	rec := do(t, h, "GET", "/availability?flight=AA100&class=M", "")
	if strings.TrimSpace(rec.Body.String()) != `{"seats":3}` || host.calls != 0 {
		t.Errorf("got %q with %d host calls", rec.Body.String(), host.calls)
	}
}

func TestWashDropsClosedOffersInsideTheTopAndCountsThem(t *testing.T) {
	host := &fakeHost{seats: map[ac.Key]int{m100: 0, k100: 9}}
	h := newTestServer(host)
	body := `{"offers":[{"flight":"AA100","class":"M"},{"flight":"AA100","class":"K"}],"top":2}`

	rec := do(t, h, "POST", "/wash", body)
	want := `{"shown":[{"flight":"AA100","class":"K"}],"open_wrong_caught":1}`
	if rec.Code != 200 || strings.TrimSpace(rec.Body.String()) != want {
		t.Errorf("got %d %q, want %q", rec.Code, rec.Body.String(), want)
	}
}

func TestWashWithNothingLeftReturnsAnEmptyList(t *testing.T) {
	h := newTestServer(&fakeHost{seats: map[ac.Key]int{}})
	rec := do(t, h, "POST", "/wash", `{"offers":[{"flight":"AA100","class":"M"}],"top":1}`)
	want := `{"shown":[],"open_wrong_caught":1}`
	if strings.TrimSpace(rec.Body.String()) != want {
		t.Errorf("got %q, want %q", rec.Body.String(), want)
	}
}

func TestResetForgetsEveryEntry(t *testing.T) {
	host := &fakeHost{seats: map[ac.Key]int{m100: 4}}
	h := newTestServer(host)

	do(t, h, "GET", "/availability?flight=AA100&class=M", "")
	if rec := do(t, h, "POST", "/admin/reset", ""); rec.Code != 204 {
		t.Fatalf("reset status %d", rec.Code)
	}
	do(t, h, "GET", "/availability?flight=AA100&class=M", "")
	if host.calls != 2 {
		t.Errorf("host was asked %d times, want 2", host.calls)
	}
}

func TestAHostThatCannotAnswerIsReportedAndNotRemembered(t *testing.T) {
	host := &fakeHost{seats: map[ac.Key]int{m100: 4}, down: true}
	h := newTestServer(host)

	rec := do(t, h, "GET", "/availability?flight=AA100&class=M", "")
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("while the host is down: got %d %q, want 503", rec.Code, rec.Body.String())
	}

	host.down = false
	rec = do(t, h, "GET", "/availability?flight=AA100&class=M", "")
	if strings.TrimSpace(rec.Body.String()) != `{"seats":4}` {
		t.Errorf("after the host is back: got %q, want 4 seats", rec.Body.String())
	}
}

func TestWashKeepsTheOffersWhenTheHostCannotAnswer(t *testing.T) {
	h := newTestServer(&fakeHost{down: true})
	rec := do(t, h, "POST", "/wash", `{"offers":[{"flight":"AA100","class":"M"}],"top":1}`)
	want := `{"shown":[{"flight":"AA100","class":"M"}],"open_wrong_caught":0}`
	if strings.TrimSpace(rec.Body.String()) != want {
		t.Errorf("got %q, want %q", rec.Body.String(), want)
	}
}

func TestHTTPHostReadsSeatsAndReportsFailures(t *testing.T) {
	airline := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/flights/AA100/classes/M/seats" {
			_, _ = w.Write([]byte(`{"seats":4}`))
			return
		}
		http.NotFound(w, r)
	}))
	defer airline.Close()

	host := newHTTPHost(airline.URL)
	if got, err := host.Seats(m100); err != nil || got != 4 {
		t.Errorf("M seats = %d, %v; want 4", got, err)
	}
	if got, err := host.Seats(k100); err != nil || got != 0 {
		t.Errorf("an unknown class = %d, %v; want 0 seats and no error (the host answered)", got, err)
	}
}

func TestHTTPHostReportsAnErrorWhenItFails(t *testing.T) {
	airline := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		http.Error(w, "boom", http.StatusInternalServerError)
	}))
	defer airline.Close()

	if _, err := newHTTPHost(airline.URL).Seats(m100); err == nil {
		t.Error("a host that failed with 500 gave no error")
	}
}
