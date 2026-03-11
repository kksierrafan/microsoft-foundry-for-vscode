# Build the application
FROM mcr.microsoft.com/dotnet/sdk:10.0-alpine AS build
WORKDIR /src

# Copy project files for dependency resolution
COPY *.csproj* .
RUN dotnet restore {{SafeProjectName}}.csproj

# Copy files from the current directory on the host to the working directory in the container
COPY . .

RUN dotnet publish -c Release -o /app -p:AssemblyName=app

# Run the application
FROM mcr.microsoft.com/dotnet/aspnet:10.0-alpine AS final
WORKDIR /app

# Copy everything needed to run the app from the "build" stage.
COPY --from=build /app .

EXPOSE 8088
ENTRYPOINT ["dotnet", "app.dll"]
