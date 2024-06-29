package main

import (
	"log"
	"net/http"

	"github.com/grrom/bank-statement-reader/function"
)

func main() {
	http.HandleFunc("/", handler)
	log.Fatal(http.ListenAndServe(":8080", nil))
}

func handler(w http.ResponseWriter, r *http.Request) {
	function.ProcessBankStatement()
}
