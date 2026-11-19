Option Explicit

' CAMS CATIA V5 Geometry Inspector V3.3
' Purpose:
'   Read-only diagnostic of existing CATPart feature definitions.
'   Does NOT modify source CATParts.
'   Does NOT create assembly constraints.
'
' Run inside CATIA V5:
'   Tools > Macro > Macros... > Visual Basic Projects > Select this .bas
'   Run CATMain
'
' Output:
'   C:\CAMS_CATIA\output\CAMS_GEOMETRY_INSPECTION_V3_3.txt

Private gFSO As Object
Private gTS As Object

Public Sub CATMain()
    On Error GoTo FatalError

    Dim baseDir As String
    Dim outDir As String
    Dim outputFile As String
    Dim files As Variant
    Dim keys As Variant
    Dim i As Long
    Dim doc As Object

    baseDir = "C:\CAMS_CATIA"
    outDir = baseDir & "\output"
    outputFile = outDir & "\CAMS_GEOMETRY_INSPECTION_V3_3.txt"

    Set gFSO = CreateObject("Scripting.FileSystemObject")
    If Not gFSO.FolderExists(outDir) Then
        gFSO.CreateFolder outDir
    End If
    Set gTS = gFSO.CreateTextFile(outputFile, True, True)

    WriteLine "============================================================"
    WriteLine "CAMS CATIA V5 GEOMETRY INSPECTOR V3.3"
    WriteLine "Read-only Sketch / Pad parameter inspection"
    WriteLine "============================================================"
    WriteLine "CATIA Version: " & SafeVersion()
    WriteLine "Timestamp: " & CStr(Now)
    WriteLine ""

    keys = Array("ROW1", "ROW23_COMMON", "ROW2", "ROW3")
    files = Array( _
        outDir & "\CAMS_ROW1.CATPart", _
        outDir & "\CAMS_ROW23_COMMON.CATPart", _
        outDir & "\CAMS_ROW2.CATPart", _
        outDir & "\CAMS_ROW3.CATPart")

    For i = LBound(files) To UBound(files)
        WriteLine ""
        WriteLine "############################################################"
        WriteLine "PART KEY: " & CStr(keys(i))
        WriteLine "FILE: " & CStr(files(i))
        WriteLine "############################################################"

        If gFSO.FileExists(CStr(files(i))) Then
            Set doc = GetOrOpenDocument(CStr(files(i)))
            If doc Is Nothing Then
                WriteLine "[ERROR] Could not open/find document."
            Else
                InspectDocument doc, CStr(keys(i))
            End If
        Else
            WriteLine "[ERROR] File not found."
        End If
    Next i

    WriteLine ""
    WriteLine "============================================================"
    WriteLine "INSPECTION COMPLETE"
    WriteLine "No source CATPart geometry was intentionally modified."
    WriteLine "============================================================"

    gTS.Close
    Set gTS = Nothing
    MsgBox "CAMS V3.3 inspection complete." & vbCrLf & outputFile, vbInformation
    Exit Sub

FatalError:
    On Error Resume Next
    If Not gTS Is Nothing Then
        WriteLine "[FATAL ERROR] " & Err.Number & " : " & Err.Description
        gTS.Close
    End If
    MsgBox "V3.3 failed: " & Err.Number & " - " & Err.Description, vbCritical
End Sub

Private Function SafeVersion() As String
    On Error Resume Next
    SafeVersion = CATIA.Version
    If Err.Number <> 0 Then
        Err.Clear
        SafeVersion = "Unavailable"
    End If
End Function

Private Function GetOrOpenDocument(ByVal fullPath As String) As Object
    On Error GoTo OpenNew
    Dim d As Object
    For Each d In CATIA.Documents
        If LCase(CStr(d.FullName)) = LCase(fullPath) Then
            Set GetOrOpenDocument = d
            Exit Function
        End If
    Next d

OpenNew:
    Err.Clear
    On Error GoTo Failed
    Set GetOrOpenDocument = CATIA.Documents.Open(fullPath)
    Exit Function
Failed:
    WriteLine "[OPEN ERROR] " & Err.Number & " : " & Err.Description
    Set GetOrOpenDocument = Nothing
End Function

Private Sub InspectDocument(ByVal doc As Object, ByVal partKey As String)
    On Error GoTo DocError

    Dim part As Object
    Dim bodies As Object
    Dim body As Object
    Dim shapes As Object
    Dim shp As Object
    Dim sketches As Object
    Dim sk As Object
    Dim i As Long

    WriteLine "Document.Name: " & SafeString(doc.Name)
    WriteLine "Document.FullName: " & SafeString(doc.FullName)

    Set part = doc.Part
    WriteLine "Part.Name: " & SafeString(part.Name)

    Set bodies = part.Bodies
    WriteLine "Part.Bodies.Count: " & CStr(bodies.Count)

    For i = 1 To bodies.Count
        Set body = bodies.Item(i)
        WriteLine ""
        WriteLine "  BODY[" & CStr(i) & "]: " & SafeString(body.Name)

        On Error Resume Next
        Set shapes = body.Shapes
        If Err.Number <> 0 Then
            WriteLine "    Shapes collection error: " & Err.Number & " - " & Err.Description
            Err.Clear
        Else
            WriteLine "    Shapes.Count: " & CStr(shapes.Count)
            Dim j As Long
            For j = 1 To shapes.Count
                Set shp = shapes.Item(j)
                InspectShape shp, j
            Next j
        End If
        On Error GoTo DocError
    Next i

    Set sketches = part.Sketches
    WriteLine ""
    WriteLine "Part.Sketches.Count: " & CStr(sketches.Count)
    For i = 1 To sketches.Count
        Set sk = sketches.Item(i)
        InspectSketch sk, i
    Next i

    Exit Sub
DocError:
    WriteLine "[DOCUMENT ERROR] " & Err.Number & " : " & Err.Description
    Err.Clear
End Sub

Private Sub InspectShape(ByVal shp As Object, ByVal index As Long)
    On Error Resume Next
    WriteLine "    SHAPE[" & CStr(index) & "] Name=" & SafeString(shp.Name) & _
              " TypeName=" & TypeName(shp)

    Dim v As Variant
    Err.Clear
    v = CallByName(shp, "FirstLimit", VbGet)
    If Err.Number = 0 Then
        WriteLine "      FirstLimit.TypeName=" & TypeName(v)
        DumpLimit v, "FirstLimit"
    Else
        WriteLine "      FirstLimit: unavailable (" & Err.Number & " - " & Err.Description & ")"
    End If

    Err.Clear
    v = CallByName(shp, "SecondLimit", VbGet)
    If Err.Number = 0 Then
        WriteLine "      SecondLimit.TypeName=" & TypeName(v)
        DumpLimit v, "SecondLimit"
    Else
        WriteLine "      SecondLimit: unavailable"
    End If

    Err.Clear
    v = CallByName(shp, "Profile", VbGet)
    If Err.Number = 0 Then
        WriteLine "      Profile.TypeName=" & TypeName(v)
        WriteLine "      Profile.Name=" & SafeString(v.Name)
    Else
        WriteLine "      Profile: unavailable (" & Err.Number & " - " & Err.Description & ")"
    End If

    Err.Clear
    v = CallByName(shp, "Direction", VbGet)
    If Err.Number = 0 Then
        WriteLine "      Direction.TypeName=" & TypeName(v)
        WriteLine "      Direction.Name=" & SafeString(v.Name)
    Else
        WriteLine "      Direction property: unavailable"
    End If
    Err.Clear
End Sub

Private Sub DumpLimit(ByVal limitObj As Object, ByVal label As String)
    On Error Resume Next
    Dim limType As Variant
    Dim dimObj As Object
    Dim val As Variant

    Err.Clear
    limType = CallByName(limitObj, "LimitMode", VbGet)
    If Err.Number = 0 Then WriteLine "      " & label & ".LimitMode=" & CStr(limType)

    Err.Clear
    Set dimObj = CallByName(limitObj, "Dimension", VbGet)
    If Err.Number = 0 And Not dimObj Is Nothing Then
        val = CallByName(dimObj, "Value", VbGet)
        If Err.Number = 0 Then
            WriteLine "      " & label & ".Dimension.Value (m)=" & FormatNumber(CDbl(val), 9)
            WriteLine "      " & label & ".Dimension.Value (mm)=" & FormatNumber(CDbl(val) * 1000#, 4)
        Else
            WriteLine "      " & label & ".Dimension.Value unavailable"
        End If
    Else
        WriteLine "      " & label & ".Dimension unavailable"
    End If
    Err.Clear
End Sub

Private Sub InspectSketch(ByVal sk As Object, ByVal index As Long)
    On Error GoTo SketchError
    WriteLine ""
    WriteLine "  SKETCH[" & CStr(index) & "]: " & SafeString(sk.Name)

    Dim axisData(8) As Double
    Dim i As Long
    On Error Resume Next
    Err.Clear
    sk.GetAbsoluteAxisData axisData
    If Err.Number = 0 Then
        WriteLine "    AbsoluteAxisData (CATIA model units, normally m):"
        For i = 0 To 8
            WriteLine "      A(" & CStr(i) & ")=" & FormatNumber(axisData(i), 9)
        Next i
    Else
        WriteLine "    GetAbsoluteAxisData failed: " & Err.Number & " - " & Err.Description
    End If

    Err.Clear
    Dim geos As Object
    Set geos = sk.GeometricElements
    If Err.Number <> 0 Then
        WriteLine "    GeometricElements unavailable: " & Err.Number & " - " & Err.Description
        Err.Clear
        Exit Sub
    End If

    WriteLine "    GeometricElements.Count: " & CStr(geos.Count)
    Dim j As Long
    Dim geo As Object
    For j = 1 To geos.Count
        Set geo = geos.Item(j)
        InspectGeometryElement geo, j
    Next j
    Exit Sub

SketchError:
    WriteLine "    [SKETCH ERROR] " & Err.Number & " : " & Err.Description
    Err.Clear
End Sub

Private Sub InspectGeometryElement(ByVal geo As Object, ByVal index As Long)
    On Error Resume Next
    WriteLine "      GEO[" & CStr(index) & "] TypeName=" & TypeName(geo) & _
              " Name=" & SafeString(geo.Name)

    Dim arr(3) As Double
    Err.Clear
    CallByName geo, "GetCoordinates", VbMethod, arr
    If Err.Number = 0 Then
        WriteLine "        Coordinates: " & FormatNumber(arr(0), 8) & ", " & _
                  FormatNumber(arr(1), 8) & ", " & FormatNumber(arr(2), 8) & ", " & _
                  FormatNumber(arr(3), 8)
    End If

    Dim p1(1) As Double
    Dim p2(1) As Double
    Err.Clear
    CallByName geo, "GetEndPoints", VbMethod, p1, p2
    If Err.Number = 0 Then
        WriteLine "        EndPoint1: " & FormatNumber(p1(0), 8) & ", " & FormatNumber(p1(1), 8)
        WriteLine "        EndPoint2: " & FormatNumber(p2(0), 8) & ", " & FormatNumber(p2(1), 8)
    End If

    Dim center(1) As Double
    Dim radius As Variant
    Err.Clear
    CallByName geo, "GetCenter", VbMethod, center
    If Err.Number = 0 Then
        WriteLine "        Center: " & FormatNumber(center(0), 8) & ", " & FormatNumber(center(1), 8)
        Err.Clear
        radius = CallByName(geo, "Radius", VbGet)
        If Err.Number = 0 Then WriteLine "        Radius: " & FormatNumber(CDbl(radius), 8)
    End If
    Err.Clear
End Sub

Private Function SafeString(ByVal value As Variant) As String
    On Error Resume Next
    SafeString = CStr(value)
    If Err.Number <> 0 Then
        Err.Clear
        SafeString = "<unavailable>"
    End If
End Function

Private Sub WriteLine(ByVal s As String)
    If Not gTS Is Nothing Then gTS.WriteLine s
End Sub
