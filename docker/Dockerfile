FROM golang:1.22

# Install necessary tools
RUN apt-get update && apt-get install -y git 

# Set the working directory inside the container
WORKDIR /workspace

COPY ../ /workspace

# Download Go modules (if go.mod and go.sum exist)
RUN if [ -f "go.mod" ] && [ -f "go.sum" ]; then go mod download; fi

# Command to run when starting the container
CMD ["go", "run", "cmd/main.go"]
