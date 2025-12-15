package main

import (
	"encoding/json"
	"net/http"
)

type Response struct {
	Message string `json:"message"`
}

func internalHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(Response{Message: "Hello from Go microservice"})
}

func main() {
	http.HandleFunc("/internal", internalHandler)
	http.ListenAndServe(":9000", nil)
}
