FROM maven:3.8-amazoncorretto-17 as maven_builder

COPY src /src/
COPY pom.xml .

RUN mvn clean package

FROM tomcat:jdk17-corretto

COPY --from=maven_builder /target/rdfconv.war /usr/local/tomcat/webapps

CMD ["catalina.sh", "run"]
